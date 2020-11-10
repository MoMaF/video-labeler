import { createSlice } from '@reduxjs/toolkit'

import {fetchClusterAsync, fetchActorsAsync} from 'features/faces/facesSlice'
import client from 'app/client'

export const sidebarSlice = createSlice({
  name: 'sidebar',
  initialState: {
    loading: true,
    movies: null,  // {name, id, year, nClusters}
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
    }
  }
})

const { setMovies, setSelectedMovie } = sidebarSlice.actions

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched
export const fetchMoviesAsync = () => dispatch => {
  client.get('movies')
    .then(response => {
      const movies = response.data
      dispatch(setMovies({movies}))

      if (movies && movies.length > 0) {
        dispatch(selectMovieAndFetch(movies[0]))
      }
    })
}

// movie = {name, id}
export const selectMovieAndFetch = movie => dispatch => {
  dispatch(setSelectedMovie({movie}))
  dispatch(fetchClusterAsync(movie.id, 0))
  dispatch(fetchActorsAsync(movie.id))
}

export default sidebarSlice.reducer
