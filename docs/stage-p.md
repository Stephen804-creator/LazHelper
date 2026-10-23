# Stage P — Progress and Activity Centre

The progress strip tracks actual in-flight API requests. It uses an indeterminate progress element because most current operations do not report measured percentage completion; LazHelper does not invent percentage values.

The Activity Centre reads a bounded local history of API request method, route, status code, timestamps, and measured duration. It also shows requests currently in flight in this server process. Prompts, request bodies, and extracted document contents are not stored in the activity log. History is limited to the latest 500 events.

This is operational visibility, not a promise of background job scheduling. Tasks that return immediately are shown as completed requests; long-running requests remain visible until the server responds.
