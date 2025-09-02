# 3. Спецификация API

### Структура схемы OpenAPI 3.1

```yaml
openapi:
info:
  title: FREESPORT API
  description: Comprehensive e-commerce API supporting B2B/B2C operations
  version: "1.0.0"
  contact:
    name: FREESPORT Development Team
    email: dev@freesport.com

servers:
  - url: https://api.freesport.com/v1
    description: Production server
  - url: https://staging-api.freesport.com/v1
    description: Staging server

security:
  - BearerAuth: []
  - ApiKeyAuth: []

paths:
  # Authentication Endpoints
  /auth/login/:
    post:
      tags: [Authentication]
      summary: User login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
              required: [email, password]
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  user:
                    $ref: '#/components/schemas/User'

  /auth/refresh/:
    post:
      tags: [Authentication]
      summary: Refresh access token
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                refresh_token:
                  type: string
              required: [refresh_token]

  # Product Catalog Endpoints  
  /products/:
    get:
      tags: [Products]
      summary: List products with filtering and pagination
      parameters:
        - name: category
          in: query
          schema:
            type: string
        - name: brand
          in: query
          schema:
            type: string
        - name: min_price
          in: query
          schema:
            type: number
        - name: max_price
          in: query
          schema:
            type: number
        - name: search
          in: query
          schema:
            type: string
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: page_size
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Products list
          content:
            application/json:
              schema:
                type: object
                properties:
                  count:
                    type: integer
                  next:
                    type: string
                    nullable: true
                  previous:
                    type: string
                    nullable: true
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/Product'

  /products/{id}/:
    get:
      tags: [Products]
      summary: Get product details
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Product details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProductDetail'

  # Cart Management
  /cart/:
    get:
      tags: [Cart]
      summary: Get current user's cart
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Cart contents
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Cart'
    
    post:
      tags: [Cart]
      summary: Add item to cart
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: integer
                quantity:
                  type: integer
                  minimum: 1
              required: [product_id, quantity]

  # Order Management
  /orders/:
    get:
      tags: [Orders]
      summary: List user orders
      security:
        - BearerAuth: []
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, confirmed, processing, shipped, delivered, cancelled]
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Orders list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrderList'
    
    post:
      tags: [Orders]
      summary: Create new order
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OrderCreate'
      responses:
        '201':
          description: Order created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
