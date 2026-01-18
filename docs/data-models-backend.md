# Data Models Documentation

## 1. Products Application

The core of the catalog system. Uses a hybrid approach for images (variant-specific with fallback to product base images).

### Core Models

- **Product**: Base product model.
  - Fields: `name`, `slug`, `brand`, `category`, `description`, `specifications` (JSONB), `base_images` (JSONB list of URLs).
  - Marketing flags: `is_hit`, `is_new`, `is_sale`, `is_promo`, `is_premium`.
  - 1C Integration: `onec_id`, `sync_status`.

- **ProductVariant**: Specific SKU (e.g., Red XL).
  - Fields: `sku`, `color_name`, `size_value`.
  - Pricing (Role-based): `retail_price`, `opt1_price`, `opt2_price`, `opt3_price`, `trainer_price`, `federation_price`.
  - Stock: `stock_quantity`, `reserved_quantity`.
  - Images: `main_image` (ImageField), `gallery_images` (JSONB list of URLs).

- **Brand**: Product manufacturers.
  - Fields: `name`, `slug`, `normalized_name` (deduplication).

- **Category**: Hierarchical category tree.
  - Fields: `name`, `slug`, `parent` (FK to self), `image`.

- **Attribute/AttributeValue**: EAV system for flexible product properties (Color, Size, Material).

### Integration Models

- **ImportSession**: Tracks 1C synchronization sessions.
- **Brand1CMapping**, **Attribute1CMapping**: Connects local IDs to 1C UUIDs for deduplication.

## 2. Users Application

Custom user model supporting B2B and B2C roles.

### Core Models

- **User**: AbstractUser extension.
  - Roles: `retail`, `wholesale_level1-3`, `trainer`, `federation_rep`, `admin`.
  - B2B Fields: `company_name`, `tax_id`, `is_verified`.
  - 1C Sync: `onec_id`, `sync_status`.

- **Company**: Extended B2B profile.
  - Fields: `legal_name`, `tax_id`, `kpp`, `bank_details`.

- **Address**: Shipping addresses.
  - Types: `shipping`, `legal`.

- **Favorite**: Wishlist functionality (User <-> Product).

## 3. Orders Application

Unified order system for all user types.

### Core Models

- **Order**:
  - Fields: `user` (nullable for guest checkout), `status`, `total_amount`.
  - Delivery: `delivery_method`, `delivery_address`, `tracking_number`.
  - Payment: `payment_method`, `payment_status`, `payment_id` (YuKassa).

- **OrderItem**:
  - Snapshot of product data at purchase time: `product_name`, `product_sku`, `unit_price`, `quantity`.
  - Links to `Product` and `ProductVariant` (SET_NULL on delete).
