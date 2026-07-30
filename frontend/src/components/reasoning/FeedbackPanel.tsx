/**
 * Feedback panel for reasoning quality
 * Allows users to rate and correct reasoning
 */

import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Button,
  Textarea,
  Select,
  useToast,
} from "@/components/ui";
import { ThumbsUp, ThumbsDown, Check, SendHorizonal } from "lucide-react";

interface FeedbackPanelProps {
  turnId: string;
  queryText: string;
  answerGiven: string;
  reasoningPath?: string[];
  className?: string;
  onFeedbackSubmitted?: () => void;
}

export function FeedbackPanel({
  turnId,
  queryText,
  answerGiven,
  reasoningPath = [],
  className = "",
  onFeedbackSubmitted,
}: FeedbackPanelProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [correction, setCorrection] = useState("");
  const [correctionType, setCorrectionType] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async () => {
    if (rating === null) {
      toast.warning(
        "Rating required",
        "Please provide a rating before submitting",
      );
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch("/api/reasoning/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          turn_id: turnId,
          user_rating: rating / 100, // Convert to 0-1
          user_correction: correction || undefined,
          correction_type: correctionType || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit feedback");
      }

      setIsSubmitted(true);
      toast.success(
        "Feedback recorded",
        "Thank you! This helps improve future reasoning.",
      );

      onFeedbackSubmitted?.();
    } catch (error) {
      toast.error("Submission failed", "Please try again later");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2 text-green-600">
            <Check className="w-5 h-5" />
            <span>Feedback submitted. Thank you!</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader title="How was this reasoning?" />
      <CardContent className="space-y-4">
        {/* Rating */}
        <div className="flex gap-2">
          <Button
            variant={rating === 100 ? "primary" : "outline"}
            size="sm"
            onClick={() => setRating(100)}
            className="flex-1"
          >
            <ThumbsUp className="w-4 h-4 mr-1" />
            Correct
          </Button>
          <Button
            variant={rating === 50 ? "secondary" : "outline"}
            size="sm"
            onClick={() => setRating(50)}
            className="flex-1"
          >
            Partial
          </Button>
          <Button
            variant={rating === 0 ? "danger" : "outline"}
            size="sm"
            onClick={() => setRating(0)}
            className="flex-1"
          >
            <ThumbsDown className="w-4 h-4 mr-1" />
            Wrong
          </Button>
        </div>

        {/* Correction type */}
        {rating !== null && rating < 100 && (
          <Select
            value={correctionType}
            onChange={setCorrectionType}
            placeholder="What was wrong?"
            options={[
              { value: "factual", label: "Factual error" },
              { value: "incomplete", label: "Incomplete answer" },
              { value: "wrong_inference", label: "Wrong inference" },
              { value: "irrelevant", label: "Irrelevant information" },
            ]}
          />
        )}

        {/* Correction text */}
        {rating !== null && rating < 100 && (
          <Textarea
            placeholder="What should the answer have been? (optional)"
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            rows={3}
          />
        )}

        {/* Submit */}
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || rating === null}
          className="w-full"
        >
          <SendHorizonal className="w-4 h-4 mr-2" />
          {isSubmitting ? "Submitting..." : "Submit Feedback"}
        </Button>
      </CardContent>
    </Card>
  );
}
