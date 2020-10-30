import { createSlice } from '@reduxjs/toolkit'
import axios from 'axios'

export const facesSlice = createSlice({
  name: 'faces',
  initialState: {
    loading: true,
    movieId: null,
    clusterId: null,
    images: [], // {url, approved}
    actors: [], // {id, name}
    selectedActorId: null, // label
  },
  reducers: {
    setCluster: (state, action) => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes
      state.loading = false
      state.clusterId = action.payload.clusterId
      state.movieId = action.payload.movieId
      state.images = action.payload.images
    },
    setActors: (state, action) => {
      state.actors = action.payload.actors
    },
    setSelectedActor: (state, action) => {
      if (state.selectedActorId === action.payload.selectedActorId) {
        state.selectedActorId = null
      } else {
        state.selectedActorId = action.payload.selectedActorId
      }
    },
    toggleImage: (state, action) => {
      const i = action.payload.imageIndex
      state.images[i].approved = !state.images[i].approved
    }
  }
})

const { setCluster } = facesSlice.actions
export const { toggleImage, setActors, setSelectedActor } = facesSlice.actions

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched
// /faces/clusters/images/{movie_id}/{cluster_id}
export const fetchClusterAsync = (movieId, clusterId) => dispatch => {
  axios.get(`http://localhost:5000/faces/clusters/images/${movieId}/${clusterId}`)
    .then(response => {
      const {images, label} = response.data
      dispatch(setCluster({
        movieId,
        clusterId,
        images,
      }))
      dispatch(setSelectedActor({selectedActorId: label}))
    })
}

export const sendClusterAsync = (movieId, clusterId, images, label) => {
  axios.post(
    `http://localhost:5000/faces/clusters/images/${movieId}/${clusterId}`,
    {label, images},
  ).then(_ => console.log("Send data for cluster: " + clusterId))
  .catch(_ => console.log("FAILED for cluster: " + clusterId))
}

export const fetchActorsAsync = movieId => dispatch => {
  axios.get(`http://localhost:5000/actors/${movieId}`)
    .then(response => {
      const actors = response.data
      dispatch(setActors({actors}))
    })
}

// The function below is called a selector and allows us to select a value from
// the state. Selectors can also be defined inline where they're used instead of
// in the slice file. For example: `useSelector((state) => state.counter.value)`
export const selectLoading = state => state.faces.loading
export const selectData = state => ({
  clusterId: state.faces.clusterId,
  images: state.faces.images,
})

export default facesSlice.reducer
