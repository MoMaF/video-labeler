import React, { Component } from 'react'
import FaceView from './features/faces/FaceView'
import Sidebar from './features/sidebar/Sidebar'
import HoverView from './features/hover_view/HoverView'
import {keyDown, keyUp} from './features/hover_view/hoverSlice'
import store from './app/store'
import './App.css'

// Set REACT_APP_VERSION before running npm run start/build
const { REACT_APP_VERSION: appVersion } = process.env

const keyDownHelper = event => store.dispatch(keyDown({key: event.key}))
const keyUpHelper = event => store.dispatch(keyUp({key: event.key}))

class App extends Component {
  componentDidMount() {
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
          <div></div>
          <div>
            <h3>Video corpus labeler</h3>
          </div>
          <div>
            <p className="version">
              v{appVersion}<span> </span>
              (<a href="https://gist.github.com/ekreutz/e35a8abe20d4018289f0d19086bcc435">instructions</a>)
            </p>
          </div>
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
