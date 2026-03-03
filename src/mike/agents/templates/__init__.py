"""Code templates for the Rebuilder Agent.

Provides templates for various project types and languages.
"""

# Python FastAPI Template
PYTHON_FASTAPI_TEMPLATE = """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{project_name}",
    description="{description}",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to {project_name}"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
"""

# Python Flask Template
PYTHON_FLASK_TEMPLATE = """
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello():
    return jsonify({"message": "Welcome to {project_name}"})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True)
"""

# Python CLI Template
PYTHON_CLI_TEMPLATE = '''
import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """{project_name} CLI"""
    pass

@cli.command()
def hello():
    """Say hello"""
    console.print("[bold green]Hello from {project_name}![/bold green]")

if __name__ == "__main__":
    cli()
'''

# JavaScript Express Template
JS_EXPRESS_TEMPLATE = """
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
    res.json({ message: "Welcome to {project_name}" });
});

app.get('/health', (req, res) => {
    res.json({ status: "healthy" });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = app;
"""

# TypeScript Express Template
TS_EXPRESS_TEMPLATE = """
import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/', (req: Request, res: Response) => {
    res.json({ message: "Welcome to {project_name}" });
});

app.get('/health', (req: Request, res: Response) => {
    res.json({ status: "healthy" });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

export default app;
"""

# Go Gin Template
GO_GIN_TEMPLATE = """
package main

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

func main() {
    r := gin.Default()
    
    r.GET("/", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "message": "Welcome to {project_name}",
        })
    })
    
    r.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status": "healthy",
        })
    })
    
    r.Run(":8080")
}
"""

# Go Echo Template
GO_ECHO_TEMPLATE = """
package main

import (
    "github.com/labstack/echo/v4"
    "github.com/labstack/echo/v4/middleware"
    "net/http"
)

func main() {
    e := echo.New()
    
    e.Use(middleware.Logger())
    e.Use(middleware.Recover())
    
    e.GET("/", func(c echo.Context) error {
        return c.JSON(http.StatusOK, map[string]string{
            "message": "Welcome to {project_name}",
        })
    })
    
    e.GET("/health", func(c echo.Context) error {
        return c.JSON(http.StatusOK, map[string]string{
            "status": "healthy",
        })
    })
    
    e.Start(":8080")
}
"""

# Multi-tenant Middleware Template (Python)
PYTHON_MULTITENANT_MIDDLEWARE = '''
"""Multi-tenant middleware for request isolation."""

from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate tenant from requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from header
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID required")
        
        # Store tenant in request state
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response
'''

# Redis Client Template (Python)
PYTHON_REDIS_CLIENT = '''
"""Redis client wrapper for caching."""

import json
from typing import Optional, Any
import redis
from functools import wraps

class RedisCache:
    """Redis cache client wrapper."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url, decode_responses=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.client.get(key)
        return json.loads(value) if value else None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> None:
        """Set value in cache with expiration."""
        self.client.setex(key, expire, json.dumps(value))
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        self.client.delete(key)
    
    def cached(self, expire: int = 3600):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                cached_value = self.get(cache_key)
                
                if cached_value is not None:
                    return cached_value
                
                result = func(*args, **kwargs)
                self.set(cache_key, result, expire)
                return result
            return wrapper
        return decorator
'''

# JWT Auth Template (Python)
PYTHON_JWT_AUTH = '''
"""JWT Authentication utilities."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
SECRET_KEY = "your-secret-key"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
'''

# NestJS Module Template
NESTJS_MODULE_TEMPLATE = """
import { Module } from '@nestjs/common';
import { {Name}Controller } from './{name}.controller';
import { {Name}Service } from './{name}.service';

@Module({{
  controllers: [{Name}Controller],
  providers: [{Name}Service],
}})
export class {Name}Module {{}}
"""

# NestJS Controller Template
NESTJS_CONTROLLER_TEMPLATE = """
import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { {Name}Service } from './{name}.service';

@Controller('{name}')
export class {Name}Controller {{
  constructor(private readonly {name}Service: {Name}Service) {{}}

  @Get()
  findAll() {{
    return this.{name}Service.findAll();
  }}

  @Get(':id')
  findOne(@Param('id') id: string) {{
    return this.{name}Service.findOne(id);
  }}

  @Post()
  create(@Body() createDto: any) {{
    return this.{name}Service.create(createDto);
  }}
}}
"""

# NestJS Service Template
NESTJS_SERVICE_TEMPLATE = """
import { Injectable } from '@nestjs/common';

@Injectable()
export class {Name}Service {{
  private items: any[] = [];

  findAll() {{
    return this.items;
  }}

  findOne(id: string) {{
    return this.items.find(item => item.id === id);
  }}

  create(createDto: any) {{
    const newItem = {{ ...createDto, id: Date.now().toString() }};
    this.items.push(newItem);
    return newItem;
  }}
}}
"""

# Template registry
TEMPLATES = {
    "python": {
        "fastapi": PYTHON_FASTAPI_TEMPLATE,
        "flask": PYTHON_FLASK_TEMPLATE,
        "cli": PYTHON_CLI_TEMPLATE,
        "multitenant_middleware": PYTHON_MULTITENANT_MIDDLEWARE,
        "redis_client": PYTHON_REDIS_CLIENT,
        "jwt_auth": PYTHON_JWT_AUTH,
    },
    "javascript": {
        "express": JS_EXPRESS_TEMPLATE,
    },
    "typescript": {
        "express": TS_EXPRESS_TEMPLATE,
        "nestjs_module": NESTJS_MODULE_TEMPLATE,
        "nestjs_controller": NESTJS_CONTROLLER_TEMPLATE,
        "nestjs_service": NESTJS_SERVICE_TEMPLATE,
    },
    "go": {
        "gin": GO_GIN_TEMPLATE,
        "echo": GO_ECHO_TEMPLATE,
    },
}


def get_template(language: str, template_type: str) -> Optional[str]:
    """
    Get a template by language and type.

    Args:
        language: Programming language
        template_type: Type of template

    Returns:
        Template string or None if not found
    """
    return TEMPLATES.get(language, {}).get(template_type)


def render_template(template: str, variables: dict) -> str:
    """
    Render a template with variable substitution.

    Args:
        template: Template string
        variables: Dictionary of variables

    Returns:
        Rendered template string
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
        # Support TitleCase for class names
        result = result.replace(f"{{{key.title()}}}", str(value).title())
    return result
