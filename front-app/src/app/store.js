import { configureStore } from '@reduxjs/toolkit'
import counterReducer from '../features/counter/counterSlice'
import facesReducer from '../features/faces/facesSlice'
import sidebarReducer from '../features/sidebar/sidebarSlice'
import hoverReducer from '../features/hover_view/hoverSlice'

export default configureStore({
  reducer: {
    counter: counterReducer,
    faces: facesReducer,
    sidebar: sidebarReducer,
    hover: hoverReducer,
  },
})
