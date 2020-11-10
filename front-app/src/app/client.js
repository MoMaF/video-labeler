import applyCaseMiddleware from 'axios-case-converter'
import axios from 'axios'
import backendUrl from 'app/backendUrl'

const client = applyCaseMiddleware(axios.create({
    baseURL: `${backendUrl}/api/`,
    timeout: 2000,
}))

export default client
