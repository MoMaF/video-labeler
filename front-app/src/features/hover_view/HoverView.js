import React, { Component } from 'react'
import { connect } from 'react-redux'
import './HoverView.css'

const urlToImage = (imageUrl, shouldMax) => {
  return (
    <div className={`hover-image-container ${shouldMax ? "wider" : ""}`}>
      <img
        src={`http://localhost:5000/${imageUrl}`}
        className="hover-image"
        key={`image-${imageUrl}`}
      />
    </div>
  )
}

class HoverView extends Component {
  render() {
    const {hoverItem, pressedKeys} = this.props
    if (!hoverItem || !pressedKeys[hoverItem.requiredKey]) {
      return null
    }

    const threshold = window.innerHeight / 2
    const placement = (hoverItem.pos.Y < threshold) ? "bottom" : "top"

    let content = <div className="hover-empty-text">No preview images to show.</div>
    const max = hoverItem.imageUrls.length === 1
    if (hoverItem.imageUrls.length > 0) {
      content = (
        <div className="hover-image-content">
          {hoverItem.imageUrls.slice(0, 3).map(url => urlToImage(url, max))}
        </div>
      )
    }

    return (
      <div className={`hoverview ${placement}`}>
        <div className="hover-title">{hoverItem.title}</div>
        {content}
      </div>
    )
  }
}

export default connect(state => state.hover)(HoverView)
