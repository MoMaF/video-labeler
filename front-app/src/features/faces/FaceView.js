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
  setStatus,
  CLUSTER_STATUSES,
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
    this.handleStatusClicked = this.handleStatusClicked.bind(this)
  }

  handleImageClicked(imageIndex) {
    this.props.dispatch(toggleImage(imageIndex))
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

  handleStatusClicked(status) {
    this.props.dispatch(setStatus(status))
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
        console.log("Cluster dirty: SENDING TO DATABASE")
        const cluster = {
          id: clusterId,
          label: this.props.selectedActorId,
          time: Math.round((new Date()).getTime() - this.props.clusterShowTime),
          images: this.props.images,
          status: this.props.clusterStatus,
        }
        dispatch(sendClusterAsync(movieId, cluster))
      } else {
        console.log("Cluster NOT DIRTY")
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
        afterName: (actor.predicted ? " 🔮 (Predicted)" : ""),
        subTitle: actor.role,
      }))

      // Format time message about when cluster was saved in database
      let labelTimeMsg = 'No information about this cluster in the database.'
      if (labelTime !== null) {
        labelTimeMsg = 'Cluster data saved to database at '
        const d = dayjs(labelTime)
        const isToday = dayjs().isSame(d, 'day')
        let timePart = (isToday) ? "" : (d.format('MMMM D YYYY, '))
        timePart += (d.format('HH:mm:ss') + `. (${d.fromNow()})`)
        labelTimeMsg += timePart
      }

      // Render all image views of actor faces
      const imagesViews = images.map((imageData, i) => {
        const item = {
          name: "Frame " + imageData.frameIndex,
          images: [imageData.fullFrameUrl],
        }
        return (
          <div
            className="faceimg-wrap"
            onClick={this.handleImageClicked.bind(this, i)}
            onMouseEnter={this.handleElementEnter.bind(this, item)}
            onMouseLeave={this.handleElementLeave.bind(this, item)}
          >
            <div className={`faceimg-border ${imageData.status}-image`}></div>
            <img
              src={`${backendUrl}/${imageData.url}`}
              className="faceimg"
              key={imageData.url + i}
              alt={`Original URL: ${imageData.url}`}
            />
          </div>
        )
      })

      // Render the small buttons with cluster status labels
      const statusButtons = CLUSTER_STATUSES.map((status, index) => {
        const text = status[0].toUpperCase() + status.slice(1)
        const isSelected = status === this.props.clusterStatus
        const extraClass = (isSelected) ? 'selected' : ''
        const statusOnClick = (isSelected) ? null : CLUSTER_STATUSES[index]
        return (<div
          className={`status-btn ${extraClass}`}
          onClick={this.handleStatusClicked.bind(this, statusOnClick)}
        >{text}</div>)
      })

      // Compose the full view and return
      return (
        <div className="faceview">
          <div className="faceview-content">
            <div className="faceview-info">
              <div className="faceview-info-header">
                <h3>{`Cluster ${(clusterId + 1)} / ${nClusters}`}</h3>
                {statusButtons}
              </div>
              <p>{labelTimeMsg}</p>
            </div>
            <div className="faces-container">
              {imagesViews}
            </div>
          </div>
          <div className="faceview-list">
            <h3>Actors</h3>
            <ListView
              items={actors}
              itemClicked={this.handleActorClicked}
              selectedItem={this.props.selectedActorId}
              onEnter={this.handleElementEnter}
              onLeave={this.handleElementLeave}
            />
          </div>
        </div>
      )
    }
  }
}

export default connect(selectProps)(FaceView)
