import React, { useState, Component } from 'react'
import { useSelector, useDispatch, connect } from 'react-redux'
import {
  fetchClusterAsync,
  sendClusterAsync,
  toggleImage,
  setSelectedActor,
} from './facesSlice'
import { setHoverItem } from '../hover_view/hoverSlice'
import ListView from '../lists/ListView'
import './FaceView.css'

// Key required to be pressed for this view to send popup overlays
const POPUP_KEY = "Control"

const Spinner = () => (
  <div className="loader"></div>
)

class FaceView extends Component {
  constructor() {
    super()
    this.handleKeyPress = this.handleKeyPress.bind(this)
    this.handleKeyDown = this.handleKeyDown.bind(this)
    this.handleImageClicked = this.handleImageClicked.bind(this)
    this.handleActorClicked = this.handleActorClicked.bind(this)
    this.handleElementEnter = this.handleElementEnter.bind(this)
    this.handleElementLeave = this.handleElementLeave.bind(this)
  }

  handleImageClicked(imageIndex) {
    this.props.dispatch(toggleImage({imageIndex}))
  }

  handleActorClicked(actor) {
    this.props.dispatch(setSelectedActor({selectedActorId: actor.id}))
  }

  handleKeyPress(event) {
    // you may also add a filter here to skip keys, that do not have an effect for your app
    if (event.key == "Enter") {
      const {dispatch} = this.props
      dispatch(fetchClusterAsync(1))
    }
  }

  handleElementEnter(item, event) {
    const pos = {X: event.clientX, Y: event.clientY}
    const title = item.name ? item.name : ""
    const requiredKey = POPUP_KEY
    const imageUrls = item.images ? item.images : []
    console.log(item)
    this.props.dispatch(setHoverItem({hoverItem: {title, pos, imageUrls, requiredKey}}))
  }

  handleElementLeave(item, event) {
    console.log("Leave event!")
    event.preventDefault()
    this.props.dispatch(setHoverItem({hoverItem: null}))
  }

  handleKeyDown(event) {
    // arrow keys are only triggered by key down, not keypressed!
    const {dispatch} = this.props
    if (event.key == "ArrowLeft" || event.key == "ArrowRight") {
      const add = event.key == "ArrowRight" ? 1 : -1
      const {movieId, clusterId} = this.props

      // Save data for current cluster
      const label = this.props.selectedActorId
      sendClusterAsync(movieId, clusterId, this.props.images, label)

      // Get data for next cluster
      dispatch(fetchClusterAsync(movieId, clusterId + add))
    }
  }

  componentDidMount() {
     document.addEventListener('keypress', this.handleKeyPress)
     document.addEventListener('keydown', this.handleKeyDown)
  }

  componentWillUnmount() {
      document.removeEventListener('keypress', this.handleKeyPress)
      document.removeEventListener('keydown', this.handleKeyDown)
  }

  render() {
    if (this.props.loading) {
      return <Spinner />
    } else {
      const {clusterId, images, actors} = this.props
      const imagesViews = images.map((imageData, i) => {
        const item = {
          name: "Frame " + imageData.frame_index,
          images: [imageData.full_frame_url],
        }
        return <img
          src={`http://localhost:5000/${imageData.url}`}
          className={`faceimg ${(imageData.approved ? 'selected-image' : 'discarded-image')}`}
          onClick={this.handleImageClicked.bind(this, i)}
          onMouseEnter={this.handleElementEnter.bind(this, item)}
          onMouseLeave={this.handleElementLeave.bind(this, item)}
        />
      })
      return (
        <div className="faceview">
          <div className="faceview-info">
            <h3>{`Cluster ID: ${clusterId}. Showing ${images.length} images.`}</h3>
            <p>This is cool info nice.</p>
          </div>
          <div className="faces-container">
            {imagesViews}
          </div>
          <ListView
            items={actors}
            itemClicked={this.handleActorClicked}
            selectedItem={this.props.selectedActorId}
            onEnter={this.handleElementEnter}
            onLeave={this.handleElementLeave}
          />
        </div>
      )
    }
  }
}

export default connect(state => state.faces)(FaceView)
