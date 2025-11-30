'use client';

/**
 * Product Image Gallery Component (Story 12.1 - QA Fix UX-001)
 * Галерея изображений товара с поддержкой zoom/lightbox
 */

import { useState } from 'react';
import Image from 'next/image';
import type { ProductImage } from '@/types/api';

interface ProductImageGalleryProps {
  images: ProductImage[];
  productName: string;
}

export default function ProductImageGallery({ images, productName }: ProductImageGalleryProps) {
  const [selectedImage, setSelectedImage] = useState(
    images.find(img => img.is_primary) || images[0]
  );
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);

  if (!images || images.length === 0) {
    return (
      <div className="aspect-square bg-neutral-100 flex items-center justify-center rounded-lg border border-neutral-200">
        <span className="text-neutral-400">Изображение отсутствует</span>
      </div>
    );
  }

  const openLightbox = () => {
    setIsLightboxOpen(true);
  };

  const closeLightbox = () => {
    setIsLightboxOpen(false);
  };

  const navigateImage = (direction: 'prev' | 'next') => {
    const currentIndex = images.indexOf(selectedImage);
    let newIndex;

    if (direction === 'prev') {
      newIndex = currentIndex === 0 ? images.length - 1 : currentIndex - 1;
    } else {
      newIndex = currentIndex === images.length - 1 ? 0 : currentIndex + 1;
    }

    setSelectedImage(images[newIndex]);
  };

  return (
    <>
      {/* Main Image */}
      <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
        <div
          className="aspect-square relative cursor-zoom-in hover:opacity-90 transition-opacity"
          onClick={openLightbox}
          onKeyDown={e => e.key === 'Enter' && openLightbox()}
          role="button"
          tabIndex={0}
        >
          <Image
            src={selectedImage.image}
            alt={selectedImage.alt_text || productName}
            fill
            sizes="(max-width: 1024px) 100vw, 66vw"
            className="object-contain"
            priority={selectedImage.is_primary}
          />
          {/* Zoom hint icon */}
          <div className="absolute top-4 right-4 bg-white/80 backdrop-blur-sm rounded-full p-2 shadow-sm">
            <svg
              className="w-5 h-5 text-neutral-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="mt-4 grid grid-cols-4 gap-2">
          {images.map((image, index) => (
            <button
              key={index}
              onClick={() => setSelectedImage(image)}
              className={`aspect-square rounded-lg border overflow-hidden transition-all hover:border-primary-500 ${
                image === selectedImage
                  ? 'border-primary-500 border-2 ring-2 ring-primary-200'
                  : 'border-neutral-200'
              }`}
              aria-label={`Показать изображение ${index + 1}`}
            >
              <div className="relative w-full h-full">
                <Image
                  src={image.image}
                  alt={image.alt_text || `${productName} - вид ${index + 1}`}
                  fill
                  sizes="(max-width: 1024px) 25vw, 15vw"
                  className="object-contain"
                />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Lightbox Modal */}
      {isLightboxOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
          onKeyDown={e => e.key === 'Escape' && closeLightbox()}
          role="dialog"
          aria-modal="true"
          tabIndex={-1}
        >
          {/* Close button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white hover:text-neutral-300 transition-colors z-10"
            aria-label="Закрыть"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>

          {/* Previous button */}
          {images.length > 1 && (
            <button
              onClick={e => {
                e.stopPropagation();
                navigateImage('prev');
              }}
              className="absolute left-4 text-white hover:text-neutral-300 transition-colors z-10"
              aria-label="Предыдущее изображение"
            >
              <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
          )}

          {/* Image */}
          <div
            className="relative max-w-6xl max-h-[90vh] w-full h-full flex items-center justify-center p-4"
            onClick={e => e.stopPropagation()}
            onKeyDown={e => e.stopPropagation()}
            role="presentation"
          >
            <Image
              src={selectedImage.image}
              alt={selectedImage.alt_text || productName}
              fill
              sizes="90vw"
              className="object-contain"
            />
          </div>

          {/* Next button */}
          {images.length > 1 && (
            <button
              onClick={e => {
                e.stopPropagation();
                navigateImage('next');
              }}
              className="absolute right-4 text-white hover:text-neutral-300 transition-colors z-10"
              aria-label="Следующее изображение"
            >
              <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          )}

          {/* Image counter */}
          {images.length > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-sm text-white px-4 py-2 rounded-full text-sm">
              {images.indexOf(selectedImage) + 1} / {images.length}
            </div>
          )}
        </div>
      )}
    </>
  );
}
