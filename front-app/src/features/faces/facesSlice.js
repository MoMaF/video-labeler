import { createSlice } from '@reduxjs/toolkit'
import client from 'app/client'

const IMAGE_STATUSES = ["same", "different", "invalid"]

export const facesSlice = createSlice({
  name: 'faces',
  initialState: {
    loading: true,
    clusterId: null,
    clusterDirty: null,
    clusterShowTime: null,  // number, unix time in milliseconds when cluster appeared
    labelTime: null, // integer, time in milliseconds
    images: [], // {url, status}
    actors: [], // {id, name}
    selectedActorId: null, // label
    predictedActors: [], // list of actor ids (int)
  },
  reducers: {
    setCluster: (state, action) => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes
      state.loading = false
      state.clusterDirty = false
      state.clusterId = action.payload.clusterId
      state.images = action.payload.images
      state.predictedActors = action.payload.predictedActors
      const hasTime = !!action.payload.labelTime
      state.labelTime = hasTime ? action.payload.labelTime * 1000 : null
      state.clusterShowTime = (new Date()).getTime()
    },
    setActors: (state, action) => {
      state.actors = action.payload.actors
    },
    setSelectedActor: (state, action) => {
      if (action.payload.markDirty) {
        state.clusterDirty = true
      }
      state.selectedActorId = action.payload.selectedActorId
    },
    toggleImage: (state, action) => {
      if (action.payload.markDirty) {
        state.clusterDirty = true
      }
      const i = action.payload.imageIndex
      const currentIndex = IMAGE_STATUSES.findIndex(status => status === state.images[i].status)
      const nextIndex = (IMAGE_STATUSES.length + currentIndex + 1) % IMAGE_STATUSES.length
      state.images[i].status = IMAGE_STATUSES[nextIndex]
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
  client.get(`faces/clusters/images/${movieId}/${clusterId}`)
    .then(response => {
      const cluster = response.data
      dispatch(setCluster(cluster))
      const selectedActor = {selectedActorId: cluster.label, markDirty: false}
      dispatch(setSelectedActor(selectedActor))
    })
}

export const sendClusterAsync = (movieId, clusterId, images, label, time) => {
  const data = {label, images, time, status: "labeled"}
  client.post(`faces/clusters/images/${movieId}/${clusterId}`, data)
    .then(_ => console.log("Send data for cluster: " + clusterId))
    .catch(_ => console.log("FAILED for cluster: " + clusterId))
}

export const fetchActorsAsync = movieId => dispatch => {
  client.get(`actors/${movieId}`)
    .then(response => {
      const actors = response.data
      dispatch(setActors({actors}))
    })
}

// The function below is called a selector and allows us to select a value from
// the state. Selectors can also be defined inline where they're used instead of
// in the slice file. For example: `useSelector((state) => state.counter.value)`
export const selectProps = state => {
  const hasMovieSelected = state.sidebar.selectedMovie !== null
  const movieId = hasMovieSelected ? state.sidebar.selectedMovie.id : null
  const nClusters = hasMovieSelected ? state.sidebar.selectedMovie.nClusters : null

  const {predictedActors: predictedIds, ...faces} = state.faces
  const hasPredictions = faces.clusterId !== null && predictedIds.length > 0

  // Sort actor array to have predicted actors first
  const predictedList = []
  const othersList = []
  for (let i = 0; i < faces.actors.length; ++i) {
    const predicted = hasPredictions && predictedIds.includes(faces.actors[i].id)
    const actorData = {...faces.actors[i], predicted}
    if (predicted) {
      predictedList.push(actorData)
    } else {
      othersList.push(actorData)
    }
  }
  const actors = [...predictedList, ...othersList]

  return {...faces, movieId, nClusters, actors}
}

export default facesSlice.reducer
