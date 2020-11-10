import applyCaseMiddleware from 'axios-case-converter'
import axios from 'axios'

// Locally, set REACT_APP_API_URL to something like: http://localhost:5000/api/
let { REACT_APP_API_URL: apiUrl } = process.env

if (!apiUrl) {
    apiUrl = `${window.location.origin}/api/`
}

console.log("Using URL: " + apiUrl)

const client = applyCaseMiddleware(axios.create({
    baseURL: apiUrl,
    timeout: 2000,
}))

export default client
