import React from 'react'
import PropTypes from 'prop-types'
import { TextField } from '@material-ui/core'

const propTypes = {
    placeholder: PropTypes.string
}

const SearchBar = (props) => {
    return (
        <TextField id='standard-basic' label={props.placeholder} />
    ) 
}

SearchBar.propTypes = propTypes

export default SearchBar