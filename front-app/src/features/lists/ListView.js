import React, { useState, Component } from 'react'

import './ListView.css'

export default class ListView extends Component {
    render() {
        const onClicked = this.props.itemClicked ? this.props.itemClicked : () => {}
        const onEnter = this.props.onEnter ? this.props.onEnter : () => {}
        const onLeave = this.props.onLeave ? this.props.onLeave : () => {}
        const childViews = this.props.items.map(item => {
            const extraClass = (item.id === this.props.selectedItem) ? "selected" : ""
            return <div
                className={`list-child ${extraClass}`}
                onClick={onClicked.bind(this, item)}
                key={item.id}
                onMouseEnter={onEnter.bind(this, item)}
                onMouseLeave={onLeave.bind(this, item)}
            >{item.name}</div>
        })
        return (
            <div className="listview">
                {childViews}
            </div>
        )
    }
}
