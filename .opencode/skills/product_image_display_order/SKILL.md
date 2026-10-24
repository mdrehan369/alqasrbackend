---
name: product_image_display_order
description: Handle product image display orders - consecutive, shifting on delete, clamping on out of range
---
## What I do
- Ensure display_order values are consecutive starting at 0
- When a middle image is deleted, shift orders of remaining images down so they stay consecutive
- When reordering to a position beyond max, clamp to the last valid position
- When reordering, shift the range of affected images appropriately
- Handle primary image promotion correctly
- Validate payloads

## When to use me
When dealing with product image display order, reordering, deletion, or adding images
