# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from __future__ import absolute_import
import codecs
from functools import partial
from six.moves.urllib.parse import urlsplit
import logger
from scrapy.exceptions import CloseSpider, NotConfigured
from scrapy import signals
from scrapy.utils.url import add_http_if_no_scheme
from twisted.internet import task

from .expire import Proxies, exp_backoff_full_jitter

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class RotatingProxyMiddleware(object):
    """
    Scrapy downloader middleware which choses a random proxy for each request.
    To enable it, add it and BanDetectionMiddleware
    to DOWNLOADER_MIDDLEWARES option::
        DOWNLOADER_MIDDLEWARES = {
            # ...
            'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
            'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
            # ...
        }
    It keeps track of dead and alive proxies and avoids using dead proxies.
    Proxy is considered dead if request.meta['_ban'] is True, and alive
    if request.meta['_ban'] is False; to set this meta key use
    BanDetectionMiddleware.
    Dead proxies are re-checked with a randomized exponential backoff.
    By default, all default Scrapy concurrency options (DOWNLOAD_DELAY,
    AUTHTHROTTLE_..., CONCURRENT_REQUESTS_PER_DOMAIN, etc) become per-proxy
    for proxied requests when RotatingProxyMiddleware is enabled.
    For example, if you set CONCURRENT_REQUESTS_PER_DOMAIN=2 then
    spider will be making at most 2 concurrent connections to each proxy.
    Settings:
    * ``ROTATING_PROXY_LIST``  - a list of proxies to choose from;
    * ``ROTATING_PROXY_LIST_PATH``  - path to a file with a list of proxies;
    * ``ROTATING_PROXY_LOGSTATS_INTERVAL`` - stats logging interval in seconds,
      30 by default;
    * ``ROTATING_PROXY_CLOSE_SPIDER`` - When True, spider is stopped if
      there are no alive proxies. If False (default), then when there is no
      alive proxies all dead proxies are re-checked.
    * ``ROTATING_PROXY_PAGE_RETRY_TIMES`` - a number of times to retry
      downloading a page using a different proxy. After this amount of retries
      failure is considered a page failure, not a proxy failure.
      Think of it this way: every improperly detected ban cost you
      ``ROTATING_PROXY_PAGE_RETRY_TIMES`` alive proxies. Default: 5.
    * ``ROTATING_PROXY_BACKOFF_BASE`` - base backoff time, in seconds.
      Default is 300 (i.e. 5 min).
    * ``ROTATING_PROXY_BACKOFF_CAP`` - backoff time cap, in seconds.
      Default is 3600 (i.e. 60 min).
    """
    def __init__(self, proxy_list, logstats_interval, stop_if_no_proxies,
                 max_proxies_to_try, backoff_base, backoff_cap, crawler):

        backoff = partial(exp_backoff_full_jitter, base=backoff_base, cap=backoff_cap)
        self.proxies = Proxies(self.cleanup_proxy_list(proxy_list),
                               backoff=backoff)
        self.logstats_interval = logstats_interval
        self.reanimate_interval = 5
        self.stop_if_no_proxies = stop_if_no_proxies
        self.max_proxies_to_try = max_proxies_to_try
        self.stats = crawler.stats

        self.log_task = None
        self.reanimate_task = None

    @classmethod
    def from_crawler(cls, crawler):
        s = crawler.settings
        proxy_path = s.get('ROTATING_PROXY_LIST_PATH', None)
        if proxy_path is not None:
            with codecs.open(proxy_path, 'r', encoding='utf8') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
        else:
            proxy_list = s.getlist('ROTATING_PROXY_LIST')
        if not proxy_list:
            raise NotConfigured()
        mw = cls(
            proxy_list=proxy_list,
            logstats_interval=s.getfloat('ROTATING_PROXY_LOGSTATS_INTERVAL', 30),
            stop_if_no_proxies=s.getbool('ROTATING_PROXY_CLOSE_SPIDER', False),
            max_proxies_to_try=s.getint('ROTATING_PROXY_PAGE_RETRY_TIMES', 5),
            backoff_base=s.getfloat('ROTATING_PROXY_BACKOFF_BASE', 300),
            backoff_cap=s.getfloat('ROTATING_PROXY_BACKOFF_CAP', 3600),
            crawler=crawler,
        )
        crawler.signals.connect(mw.engine_started,
                                signal=signals.engine_started)
        crawler.signals.connect(mw.engine_stopped,
                                signal=signals.engine_stopped)
        return mw

    def engine_started(self):
        if self.logstats_interval:
            self.log_task = task.LoopingCall(self.log_stats)
            self.log_task.start(self.logstats_interval, now=True)

        if self.reanimate_interval:
            self.reanimate_task = task.LoopingCall(self.reanimate_proxies)
            self.reanimate_task.start(self.reanimate_interval, now=False)

    def reanimate_proxies(self):
        n_reanimated = self.proxies.reanimate()
        if n_reanimated:
            logger.debug("%s proxies moved from 'dead' to 'reanimated'",
                         n_reanimated)

    def engine_stopped(self):
        if self.log_task and self.log_task.running:
            self.log_task.stop()

        if self.reanimate_task and self.reanimate_task.running:
            self.reanimate_task.stop()

    def process_request(self, request, spider):
        if 'proxy' in request.meta and not request.meta.get('_rotating_proxy'):
            return
        proxy = self.proxies.get_random()
        if not proxy:
            if self.stop_if_no_proxies:
                raise CloseSpider("no_proxies")
            else:
                logger.warn("No proxies available; marking all proxies "
                            "as unchecked")
                self.proxies.reset()
                proxy = self.proxies.get_random()
                if proxy is None:
                    logger.error("No proxies available even after a reset.")
                    raise CloseSpider("no_proxies_after_reset")

        request.meta['proxy'] = proxy
        request.meta['download_slot'] = self.get_proxy_slot(proxy)
        request.meta['_rotating_proxy'] = True

    def get_proxy_slot(self, proxy):
        """
        Return downloader slot for a proxy.
        By default it doesn't take port in account, i.e. all proxies with
        the same hostname / ip address share the same slot.
        """
        # FIXME: an option to use website address as a part of slot as well?
        return urlsplit(proxy).hostname

    def process_exception(self, request, exception, spider):
        return self._handle_result(request, spider)

    def process_response(self, request, response, spider):
        return self._handle_result(request, spider) or response

    def _handle_result(self, request, spider):
        proxy = self.proxies.get_proxy(request.meta.get('proxy', None))
        if not (proxy and request.meta.get('_rotating_proxy')):
            return
        self.stats.set_value('proxies/unchecked', len(self.proxies.unchecked) - len(self.proxies.reanimated))
        self.stats.set_value('proxies/reanimated', len(self.proxies.reanimated))
        self.stats.set_value('proxies/mean_backoff', self.proxies.mean_backoff_time)
        ban = request.meta.get('_ban', None)
        if ban is True:
            self.proxies.mark_dead(proxy)
            self.stats.set_value('proxies/dead', len(self.proxies.dead))
            return self._retry(request, spider)
        elif ban is False:
            self.proxies.mark_good(proxy)
            self.stats.set_value('proxies/good', len(self.proxies.good))

    def _retry(self, request, spider):
        retries = request.meta.get('proxy_retry_times', 0) + 1
        max_proxies_to_try = request.meta.get('max_proxies_to_try',
                                              self.max_proxies_to_try)

        if retries <= max_proxies_to_try:
            logger.debug("Retrying %(request)s with another proxy "
                         "(failed %(retries)d times, "
                         "max retries: %(max_proxies_to_try)d)",
                         {'request': request, 'retries': retries,
                          'max_proxies_to_try': max_proxies_to_try},
                         extra={'spider': spider})
            retryreq = request.copy()
            retryreq.meta['proxy_retry_times'] = retries
            retryreq.dont_filter = True
            return retryreq
        else:
            logger.debug("Gave up retrying %(request)s (failed %(retries)d "
                         "times with different proxies)",
                         {'request': request, 'retries': retries},
                         extra={'spider': spider})

    def log_stats(self):
        logger.info('%s' % self.proxies)

    @classmethod
    def cleanup_proxy_list(cls, proxy_list):
        lines = [line.strip() for line in proxy_list]
        return list({
            add_http_if_no_scheme(url)
            for url in lines
            if url and not url.startswith('#')
        })


class ScrapeStocksSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ScrapeStocksDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
