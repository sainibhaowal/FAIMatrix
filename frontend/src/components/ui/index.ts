/* =============================================================================
   FAIM UI Component Library
   
   Barrel export file for all UI components.
   Usage: import { Button, Card, Toast, ... } from "@/components/ui";
============================================================================= */

// Button
export { Button, buttonVariants } from "./Button";
export type { ButtonProps } from "./Button";

// Card
export { Card, CardHeader, CardContent, CardFooter } from "./Card";
export type { CardProps, CardHeaderProps } from "./Card";

// Toast
export { ToastProvider, useToast } from "./Toast";

// Spinner & Skeleton
export { Spinner, Skeleton, SkeletonText, SkeletonCard } from "./Spinner";
export type { SpinnerProps, SkeletonProps, SkeletonTextProps } from "./Spinner";

// EmptyState & ErrorState
export { EmptyState, ErrorState } from "./EmptyState";
export type { EmptyStateProps, ErrorStateProps } from "./EmptyState";

// Badge
export { Badge, StatusBadge } from "./Badge";
export type { BadgeProps, StatusBadgeProps } from "./Badge";

// Input
export { Input, SearchInput, Textarea } from "./Input";
export type { InputProps, SearchInputProps, TextareaProps } from "./Input";

// Progress
export { Progress, CircularProgress } from "./Progress";
export type { ProgressProps, CircularProgressProps } from "./Progress";

// Modal
export { Modal, ConfirmDialog } from "./Modal";
export type { ModalProps, ConfirmDialogProps } from "./Modal";

// Tooltip & Tabs
export { Tooltip, Tabs } from "./Tooltip";
export type { TooltipProps, Tab, TabsProps } from "./Tooltip";

// Select
export { Select, MultiSelect } from "./Select";
export type { SelectProps, SelectOption, MultiSelectProps } from "./Select";

// Theme
export { OmniGlowBG, GlassPanel, GlassCard } from "./Theme";
