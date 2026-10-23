# Stage P — Progress and Activity Centre

LazHelper shows an indeterminate progress strip while API requests are running. It does not invent completion percentages. The local Activity Centre records request route, HTTP status, timestamps, and measured duration, with a retention cap of 500 events. Request bodies, prompts, and extracted document content are not recorded.

The activity API is `GET /api/activity?limit=50`. It returns active requests and recent completed requests. The UI loads activity automatically and offers a manual refresh.

Run the project test suite before merging this stage. Review privacy and retention behavior when changing activity fields.
