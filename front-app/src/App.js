import React, { Component } from 'react'
import logo from './logo.svg'
import { Counter } from './features/counter/Counter'
import FaceView from './features/faces/FaceView'
import Sidebar from './features/sidebar/Sidebar'
import HoverView from './features/hover_view/HoverView'
import {keyDown, keyUp} from './features/hover_view/hoverSlice'
import store from './app/store'
import './App.css'

const keyDownHelper = event => store.dispatch(keyDown({key: event.key}))
const keyUpHelper = event => store.dispatch(keyUp({key: event.key}))

class App extends Component {
  componentDidMount() {
    console.log("Mounted!")
    document.addEventListener('keydown', keyDownHelper)
    document.addEventListener('keyup', keyUpHelper)
  }

  componentWillUnmount() {
    document.removeEventListener('keydown', keyDownHelper)
    document.removeEventListener('keyup', keyUpHelper)
  }

  render() {
    return (
      <div className="app">
        <HoverView />
        <header>
          <h3>Video corpus labeler</h3>
        </header>
        <div className="side-bar">
          <Sidebar />
        </div>
        <div className="content">
          <FaceView />
        </div>
      </div>
    )
  }
}

export default App
