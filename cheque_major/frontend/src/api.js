export class ApiError extends Error {
  constructor(message, status = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest(url, options = {}) {
  let response
  try {
    response = await fetch(url, options)
  } catch {
    throw new ApiError(
      'Cannot reach the backend server. Make sure it is running on port 5000 (python app.py).'
    )
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    if (data?.error) {
      throw new ApiError(data.error, response.status)
    }
    if (response.status >= 500 && !text) {
      throw new ApiError(
        'The backend returned an empty error. Check the backend terminal for the traceback.',
        response.status
      )
    }
    throw new ApiError(`Request failed with status ${response.status}`, response.status)
  }

  if (data === null) {
    throw new ApiError('The backend returned an empty or invalid response.', response.status)
  }
  return data
}
