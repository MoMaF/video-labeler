import { createSlice } from '@reduxjs/toolkit'
import client from 'app/client'
import { fetchMovieAsync } from 'features/sidebar/sidebarSlice'

// Cluster and image statuses that match those of the database
const IMAGE_STATUSES = ['same', 'different', 'invalid']
export const CLUSTER_STATUSES = ['postponed', 'discarded', 'mixed']
const DEFAULT_CLUSTER_STATUS = 'labeled'

export const facesSlice = createSlice({
  name: 'faces',
  initialState: {
    loading: true,
    clusterId: null,
    clusterStatus: DEFAULT_CLUSTER_STATUS,
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
      state.clusterStatus = action.payload.status
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
      state.clusterDirty = true
      const i = action.payload
      const currentIndex = IMAGE_STATUSES.findIndex(status => status === state.images[i].status)
      const nextIndex = (currentIndex + 1) % IMAGE_STATUSES.length
      state.images[i].status = IMAGE_STATUSES[nextIndex]
    },
    setStatus: (state, action) => {
      state.clusterDirty = true
      const status = action.payload
      if (status && CLUSTER_STATUSES.includes(status)) {
        state.clusterStatus = status
      } else {
        state.clusterStatus = DEFAULT_CLUSTER_STATUS
      }
    }
  }
})

const { setCluster } = facesSlice.actions
export const { toggleImage, setActors, setSelectedActor, setStatus } = facesSlice.actions

// The function below is called a thunk and allows us to perform async logic. It
// can be dispatched like a regular action: `dispatch(incrementAsync(10))`. This
// will call the thunk with the `dispatch` function as the first argument. Async
// code can then be executed and other actions can be dispatched
export const fetchClusterAsync = (movieId, clusterId) => dispatch => {
  client.get(`faces/clusters/${movieId}/${clusterId}`)
    .then(response => {
      const cluster = response.data
      dispatch(setCluster(cluster))
      const selectedActor = {selectedActorId: cluster.label, markDirty: false}
      dispatch(setSelectedActor(selectedActor))

      // At the same time, update the window url
      const newUrl = `/movies/${movieId}/clusters/${clusterId + 1}`
      window.history.replaceState(null, document.title, window.location.origin + newUrl)
    })
}

export const sendClusterAsync = (movieId, cluster) => dispatch => {
  // Keys in cluster: label, images, time, status
  client.post(`faces/clusters/${movieId}/${cluster.id}`, cluster)
    .then(_ => {
      console.log("Send data for cluster: " + cluster.id)
      dispatch(fetchMovieAsync(movieId))
    })
    .catch(_ => console.log("FAILED for cluster: " + cluster.id))
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
  const fps = hasMovieSelected ? state.sidebar.selectedMovie.fps : null

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

  return {...faces, movieId, fps, nClusters, actors}
}

export default facesSlice.reducer
