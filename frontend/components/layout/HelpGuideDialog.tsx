'use client'

import { ProductTour } from './ProductTour'
import { getProductTourDefinition } from './productTourSteps'

interface HelpGuideDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  returnFocusRef: React.RefObject<HTMLButtonElement | null>
  pathname?: string | null
}

export function HelpGuideDialog({
  open,
  onOpenChange,
  returnFocusRef,
  pathname,
}: HelpGuideDialogProps) {
  return (
    <ProductTour
      open={open}
      onOpenChange={onOpenChange}
      returnFocusRef={returnFocusRef}
      tour={getProductTourDefinition(pathname)}
    />
  )
}
