// Locally, set REACT_APP_BACKEND to something like: http://localhost:5000
// In production it will be determined by window.location.origin
let { REACT_APP_BACKEND: backendUrl } = process.env
if (!backendUrl) {
    backendUrl = window.location.origin
}

if (backendUrl.endsWith('/')) {
    backendUrl = backendUrl.substr(0, backendUrl.length - 1)
}

export default backendUrl
