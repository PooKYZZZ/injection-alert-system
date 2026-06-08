"use client";

import React, { useState, useRef } from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";

export default function CommentsForm() {
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const summaryRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    const form = e.currentTarget;
    const formData = new FormData(form);
    const displayName = (formData.get("displayName") as string || "").trim();
    const message = (formData.get("message") as string || "").trim();

    const newErrors: string[] = [];
    const newFieldErrors: Record<string, string> = {};

    if (!displayName) {
      newErrors.push("Display Name is required.");
      newFieldErrors.displayName = "Please enter your display name.";
    } else if (displayName.length < 2) {
      newErrors.push("Display Name must be at least 2 characters long.");
      newFieldErrors.displayName = "Display Name is too short (minimum 2 characters).";
    }

    if (!message) {
      newErrors.push("Your Message is required.");
      newFieldErrors.message = "Please enter your message.";
    } else if (message.length < 5) {
      newErrors.push("Message must be at least 5 characters long.");
      newFieldErrors.message = "Message is too short (minimum 5 characters).";
    }

    if (newErrors.length > 0) {
      e.preventDefault();
      setErrors(newErrors);
      setFieldErrors(newFieldErrors);
      setTimeout(() => {
        summaryRef.current?.focus();
        summaryRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 50);
    } else {
      setErrors([]);
      setFieldErrors({});
    }
  };

  return (
    <div className="border-t border-gray-200 pt-6 font-sans">
      <h3 className="text-xs font-bold text-slate-800 uppercase tracking-widest mb-2" id="comments-form-title">
        Post a Citizen Comment
      </h3>
      <p className="text-[11px] text-gray-500 mb-4 leading-relaxed">
        A red asterisk (<span className="text-red-600 font-bold" aria-hidden="true">*</span>) indicates a required field.
      </p>

      {errors.length > 0 && (
        <div
          ref={summaryRef}
          tabIndex={-1}
          className="mb-5 p-4 bg-red-50 border border-red-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
          aria-labelledby="comment-error-heading"
        >
          <div className="flex gap-2.5 items-start">
            <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <h4 id="comment-error-heading" className="text-xs font-bold text-red-950 uppercase tracking-wider">
                Please check the required fields below before submitting
              </h4>
              <ul className="list-disc pl-4 mt-2 space-y-1 text-xs text-red-800">
                {errors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Citizen Comments Form using precise rules: Normal HTML POST matching POST /comments/submit */}
      <form
        id="citizen-comments-form"
        action="/comments/submit"
        method="post"
        onSubmit={handleSubmit}
        className="space-y-4"
        noValidate
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="comments-input-displayName" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
              Display Name <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <input
              id="comments-input-displayName"
              type="text"
              name="displayName"
              placeholder="e.g., Maria Santos"
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.displayName}
              aria-describedby={fieldErrors.displayName ? "comments-input-displayName-error" : undefined}
              className={`w-full bg-white border ${
                fieldErrors.displayName ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 transition-colors`}
            />
            {fieldErrors.displayName && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="comments-input-displayName-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.displayName}
              </p>
            )}
          </div>
        </div>

        <div>
          <label htmlFor="comments-input-message" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">
            Your Message <span className="text-red-600 font-bold" aria-hidden="true">*</span>
          </label>
          <textarea
            id="comments-input-message"
            name="message"
            rows={3}
            placeholder="e.g., The lookup database index matches and updates instantly..."
            required
            aria-required="true"
            aria-invalid={!!fieldErrors.message}
            aria-describedby={fieldErrors.message ? "comments-input-message-error" : undefined}
            className={`w-full bg-white border ${
              fieldErrors.message ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
            } rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 transition-colors`}
          ></textarea>
          {fieldErrors.message && (
            <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="comments-input-message-error">
              <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.message}
            </p>
          )}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
          <span className="text-[10px] text-gray-400 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
            Public and searchable registry
          </span>
          <button
            id="submit-comment-btn"
            type="submit"
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 transition-colors text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 min-h-[44px] flex items-center justify-center"
          >
            Submit comment
          </button>
        </div>
      </form>
    </div>
  );
}
