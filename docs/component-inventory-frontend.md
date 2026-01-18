# Frontend Component Inventory

## UI Components (`src/components/ui`)
Reusable, atomic components.

- **Inputs**: `Input`, `Checkbox`, `Radio`, `Select`, `SearchField`.
- **Navigation**: `Breadcrumb`, `Pagination`, `Tabs`, `Sidebar`.
- **Feedback**: `Toast`, `Spinner`, `Modal`, `Skeleton`, `Badge`.
- **Layout**: `Card`, `Accordion`, `Drawer`, `Table`.
- **Theme Variants**: Many components have `Electric*` counterparts (e.g., `ElectricButton`, `ElectricModal`) for the alternate theme.

## Business Components (`src/components/business`)
Domain-specific components containing business logic.

- **Product**: `ProductCard`, `ProductGrid`, `ProductOptions`, `ProductImageGallery`.
- **Cart & Checkout**: `CartItemCard`, `CartSummary`, `CheckoutForm`, `AddressSection`.
- **Search**: `SearchAutocomplete`, `SearchResults`, `SidebarFilters`.
- **Profile**: `ProfileForm`, `AddressList`, `OrderCard`.

## Layout Components (`src/components/layout`)
Structural components.

- **Header/Footer**: `Header`, `Footer` (and `Electric*` variants).
- **Wrappers**: `LayoutWrapper`, `ProfileLayout`.

## Page Components (`src/components/home`, `src/components/product`, etc.)
- **Home**: `HeroSection`, `NewArrivalsSection`, `PromoSection`.
- **Product Page**: `ProductInfo`, `ProductSpecs`, `RelatedProducts`.
