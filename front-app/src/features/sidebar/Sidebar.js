import React, { Component } from 'react'
import { connect } from 'react-redux'
import ListView from 'features/lists/ListView'
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
        const movies = this.props.movies.map(movieItem => {
            const percent = movieItem.nLabeledClusters / movieItem.nClusters * 100
            return {
                ...movieItem,
                afterName: ` (${movieItem.year})`,
                subTitle: `Labeled clusters: ${percent.toFixed(1)}%`
            }
        })

        const {dispatch} = this.props
        return (
            <div className="sidebar">
            <h3>List of Movies <span className="light-text">({n})</span></h3>
            <ListView
                items={movies}
                selectedItem={this.props.selectedMovie ? this.props.selectedMovie.id : null}
                itemClicked={(movie, event) => {
                    dispatch(selectMovieAndFetch(movie, 0))
                }}
            />
            </div>
        )
    }
}

export default connect(state => state.sidebar)(Sidebar)
