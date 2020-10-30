import { createSlice } from '@reduxjs/toolkit'
import axios from 'axios'

import {fetchClusterAsync, fetchActorsAsync} from '../faces/facesSlice'

export const sidebarSlice = createSlice({
  name: 'sidebar',
  initialState: {
    loading: true,
    movies: null,  // {name, id}
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
  axios.get(`http://localhost:5000/movies`)
    .then(response => {
      const movies = response.data
      console.log("/movies response!")
      dispatch(setMovies({movies}))
    })
}

// movie = {name, id}
export const selectMovieAndFetch = movie => dispatch => {
  dispatch(setSelectedMovie({movie}))
  dispatch(fetchClusterAsync(movie.id, 0))
  dispatch(fetchActorsAsync(movie.id))
}

export default sidebarSlice.reducer
