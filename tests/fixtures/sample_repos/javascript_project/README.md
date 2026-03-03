# Sample JavaScript Project

A sample JavaScript/Node.js project for testing the Mike pipeline.

## Structure

```
javascript_project/
├── src/
│   ├── index.js
│   ├── services/
│   │   ├── UserService.js
│   │   └── OrderService.js
│   └── utils/
│       └── helpers.js
├── tests/
│   └── index.test.js
├── package.json
└── README.md
```

## Installation

```bash
npm install
```

## Usage

```javascript
const { UserService } = require('./src/services/UserService');

const service = new UserService();
const user = await service.getUser(1);
```
