import React, { Component } from 'react'
import { connect } from 'react-redux'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import {
  fetchClusterAsync,
  sendClusterAsync,
  toggleImage,
  setSelectedActor,
  selectProps,
} from './facesSlice'
import './FaceView.css'
import { setHoverItem } from 'features/hover_view/hoverSlice'
import ListView from 'features/lists/ListView'
import backendUrl from 'app/backendUrl'

dayjs.extend(relativeTime)
dayjs.extend(utc)

// Key required to be pressed for this view to send popup overlays
const POPUP_KEY = 'Control'

const Spinner = () => (
  <div className='loader'></div>
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
    this.props.dispatch(toggleImage({imageIndex, markDirty: true}))
  }

  handleActorClicked(actor) {
    let actorId = actor.id
    // If same actor was clicked, toggle to null!
    if (actorId === this.props.selectedActorId) {
      actorId = null
    }

    this.props.dispatch(setSelectedActor({
      selectedActorId: actorId, markDirty: true,
    }))
  }

  handleKeyPress(event) {
    // you may also add a filter here to skip keys, that do not have an effect for your app
    if (event.key === "Enter") {
      const {dispatch} = this.props
      dispatch(fetchClusterAsync(1))
    }
  }

  handleElementEnter(item, event) {
    const pos = {X: event.clientX, Y: event.clientY}
    const title = item.name ? item.name : ""
    const requiredKey = POPUP_KEY
    const imageUrls = item.images ? item.images : []
    this.props.dispatch(setHoverItem({hoverItem: {title, pos, imageUrls, requiredKey}}))
  }

  handleElementLeave(item, event) {
    event.preventDefault()
    this.props.dispatch(setHoverItem({hoverItem: null}))
  }

  handleKeyDown(event) {
    // arrow keys are only triggered by key down, not keypressed!
    const {dispatch} = this.props
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const add = event.key === "ArrowRight" ? 1 : -1
      const {movieId, clusterId, nClusters} = this.props

      // Save data for current cluster
      if (this.props.clusterDirty) {
        console.log("Cluster dirty: SENDDING")
        const label = this.props.selectedActorId
        sendClusterAsync(movieId, clusterId, this.props.images, label)
      } else {
        console.log("Cluster NOT IRTY")
      }

      // Get data for next cluster
      const nextCluster = (nClusters + clusterId + add) % nClusters
      dispatch(fetchClusterAsync(movieId, nextCluster))
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
      const {clusterId, nClusters, images, actors: rawActors, labelTime} = this.props
      const actors = rawActors.map(actor => ({
        ...actor,
        subTitle: (actor.predicted ? "Predicted correct actor" : ""),
      }))

      let labelTimeMsg = 'No information about this cluster in the database.'
      if (labelTime !== null) {
        labelTimeMsg = 'Cluster data saved to database at '
        const d = dayjs(labelTime)
        console.log(d, dayjs().utcOffset())
        const isToday = dayjs().isSame(d, 'day')
        let timePart = (isToday) ? "" : (d.format('MMMM D YYYY, '))
        timePart += (d.format('HH:mm:ss') + `. (${d.fromNow()})`)
        labelTimeMsg += timePart
      }

      const imagesViews = images.map((imageData, i) => {
        const item = {
          name: "Frame " + imageData.frameIndex,
          images: [imageData.fullFrameUrl],
        }
        return <img
          src={`${backendUrl}/${imageData.url}`}
          className={`faceimg ${(imageData.approved ? 'selected-image' : 'discarded-image')}`}
          onClick={this.handleImageClicked.bind(this, i)}
          onMouseEnter={this.handleElementEnter.bind(this, item)}
          onMouseLeave={this.handleElementLeave.bind(this, item)}
          key={imageData.url + i}
          alt={`Original URL: ${imageData.url}`}
        />
      })
      return (
        <div className="faceview">
          <div className="faceview-info">
            <h3>{`Cluster ${(clusterId + 1)} / ${nClusters}`}</h3>
          <p>{labelTimeMsg}</p>
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

export default connect(selectProps)(FaceView)
