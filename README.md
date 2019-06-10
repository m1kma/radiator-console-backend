# AWS Lambda backend for the Radiator Console
AWS Lambda backend to serve the [Radiator Console](https://github.com/m1kma/radiator-console-esp). The Lambda returns an AWS account alarms, code pipeline status and metrics as a JSON REST service.

## Deployment

The Lambda is deployed by the Serverless Framework.

```sls deploy```

## Credits
The Lambda got an inspiration from the [Radiator Exposer](https://github.com/hjhamala/radiator-exposer) made by [Heikki](https://github.com/hjhamala).

Copyright (c) Mika Mäkelä