import { createSlice } from '@reduxjs/toolkit'

import {fetchClusterAsync, fetchActorsAsync} from 'features/faces/facesSlice'
import client from 'app/client'

export const sidebarSlice = createSlice({
  name: 'sidebar',
  initialState: {
    loading: true,
    movies: null,  // {name, id, year, nClusters, nLabeledClusters}
    selectedMovie: null,
  },
  reducers: {
    setMovies: (state, action) => {
      // Reducer to set the cluster data once it has been fetched from the backend
      state.loading = false
      state.movies = action.payload.movies
    },
    setSelectedMovie: (state, action) => {
      state.selectedMovie = action.payload.movie
    },
    updateMovie: (state, action) => {
      if (state.movies !== null && state.movies.length > 0) {
        const movie = action.payload
        const i = state.movies.findIndex(({id}) => id === movie.id)
        state.movies[i] = movie
      }
    }
  }
})

const { setMovies, setSelectedMovie, updateMovie } = sidebarSlice.actions

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched

const parseUrl = () => {
  // Parse page url like: /movies/121614/clusters/2
  const path = window.location.pathname.replace(/\/$/, "")
  const pathPattern = new RegExp("^/movies/[0-9]+/clusters/[0-9]+$")
  if (!pathPattern.test(path)) {
    return [0, 0]
  }

  const parts = path.split("/")
  const movieId = parseInt(parts[2])
  const clusterId = parseInt(parts[4]) - 1
  return [movieId, clusterId]
}

export const fetchMoviesAsync = () => dispatch => {
  client.get('movies')
    .then(response => {
      const movies = response.data
      dispatch(setMovies({movies}))

      if (movies && movies.length > 0) {
        const [firstMovieId, firstClusterId] = parseUrl()
        let movie = movies.find(movie => movie.id === firstMovieId) || movies[0]
        const n = movie.nClusters
        const clusterId = (n + firstClusterId) % n
        dispatch(selectMovieAndFetch(movie, clusterId))
      }
    })
}

// Update the data of a single movie
export const fetchMovieAsync = movieId => dispatch => {
  client.get(`movies/${movieId}`)
    .then(response => {
      const movie = response.data
      dispatch(updateMovie(movie))
    })
}

// movie = {name, id}
export const selectMovieAndFetch = (movie, firstClusterId) => dispatch => {
  dispatch(setSelectedMovie({movie}))
  dispatch(fetchClusterAsync(movie.id, firstClusterId))
  dispatch(fetchActorsAsync(movie.id))
}

export default sidebarSlice.reducer
