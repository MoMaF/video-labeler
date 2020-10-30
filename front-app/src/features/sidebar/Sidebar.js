import React, { useState, Component } from 'react'
import { useSelector, useDispatch, connect } from 'react-redux'
import ListView from '../lists/ListView'
import './Sidebar.css'

import {fetchMoviesAsync, selectMovieAndFetch} from './sidebarSlice'

class Sidebar extends Component {
    componentDidMount() {
        if (this.props.loading) {
            const {dispatch} = this.props
            dispatch(fetchMoviesAsync())
        }
    }

    render() {
        if (this.props.loading) {
            return <div>Loading</div>
        }

        const n = this.props.movies.length
        const {dispatch} = this.props
        return (
            <div className="sidebar">
            <h3>List of Movies <span className="light-text">({n})</span></h3>
            <ListView
                items={this.props.movies}
                selectedItem={this.props.selectedMovie ? this.props.selectedMovie.id : null}
                itemClicked={(movie, event) => {
                    dispatch(selectMovieAndFetch(movie))
                }}
            />
            </div>
        )
    }
}

export default connect(state => state.sidebar)(Sidebar)
