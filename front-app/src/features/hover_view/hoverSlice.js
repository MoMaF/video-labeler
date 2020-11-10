import { createSlice } from '@reduxjs/toolkit'

export const hoverSlice = createSlice({
  name: 'hover',
  initialState: {
    hoverItem: null, // {title, pos, imageUrls, requiredKey}
    pressedKeys: {},
    hoverCount: 0,
  },
  reducers: {
    keyDown: (state, action) => {
      state.pressedKeys[action.payload.key] = true
    },
    keyUp: (state, action) => {
      const {key} = action.payload
      state.pressedKeys[key] = false
      if (state.hoverItem && state.hoverItem.requiredKey === key) {
        state.hoverCount = 0
      }
    },
    setHoverItem: (state, action) => {
      const {hoverItem} = action.payload
      if (hoverItem === null) {
        state.hoverCount = Math.max(state.hoverCount - 1, 0)
        if (state.hoverCount === 0) {
          state.hoverItem = null
        }
      } else {
        state.hoverCount++
        state.hoverItem = hoverItem
      }
    }
  }
})

export const { setHoverItem, keyDown, keyUp } = hoverSlice.actions

export default hoverSlice.reducer
