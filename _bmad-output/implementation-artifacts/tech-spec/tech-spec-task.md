# Marketing Banners Implementation Tasks

- [ ] **Planning & Spec**
    - [x] Create Technical Specification `tech-spec-wip.md`
    - [x] Review and Refine Specification (Avanced Elicitation)
    - [ ] Finalize Specification `tech-spec-marketing-banners.md`

- [ ] **Backend Implementation**
    - [ ] Add `BannerType` to `Banner` model
    - [ ] Create and apply migrations
    - [ ] Update `BannerAdmin`
    - [ ] Implement filtering in `ActiveBannersView` (with validation)
    - [ ] Add API tests for filtering

- [ ] **Frontend Implementation**
    - [ ] Create `useBannerCarousel` hook
    - [ ] Update `Banner` type definition
    - [ ] Update `bannersService`
    - [ ] Refactor `HeroSection` to use hook and type='hero'
    - [ ] Implement `MarketingBannersSection` using hook
    - [ ] Integrate into `HomePage`
    - [ ] Verify functionality (Manual Test)
