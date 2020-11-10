import React, { Component } from 'react'

import './ListView.css'

export default class ListView extends Component {
    render() {
        const onClicked = this.props.itemClicked ? this.props.itemClicked : () => {}
        const onEnter = this.props.onEnter ? this.props.onEnter : () => {}
        const onLeave = this.props.onLeave ? this.props.onLeave : () => {}
        const childViews = this.props.items.map(item => {
            const extraClass = (item.id === this.props.selectedItem) ? "selected" : ""
            return (<div
                    className={`list-child ${extraClass}`}
                    onClick={onClicked.bind(this, item)}
                    onMouseEnter={onEnter.bind(this, item)}
                    onMouseLeave={onLeave.bind(this, item)}
                    key={item.id}
                >
                <div className={`list-child-header ${extraClass}`}>
                    {item.name}<span>{item.afterName}</span>
                </div>
                <div className="list-child-subtitle">{item.subTitle}</div>
            </div>)
        })
        return (
            <div className="listview">
                {childViews}
            </div>
        )
    }
}
