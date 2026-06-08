"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { Ticket, AlertCircle } from "lucide-react";

export default function SupportPage() {
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const summaryRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    const form = e.currentTarget;
    const formData = new FormData(form);

    const email = (formData.get("email") as string || "").trim();
    const category = formData.get("category") as string || "";
    const subject = (formData.get("subject") as string || "").trim();
    const message = (formData.get("message") as string || "").trim();

    const newErrors: string[] = [];
    const newFieldErrors: Record<string, string> = {};

    if (!email) {
      newErrors.push("Your Email is required.");
      newFieldErrors.email = "Please enter your email address.";
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        newErrors.push("Please enter a valid email address.");
        newFieldErrors.email = "The email address format is invalid.";
      }
    }

    if (!category) {
      newErrors.push("Inquiry Category selection is required.");
      newFieldErrors.category = "Please select an inquiry category.";
    }

    if (!subject) {
      newErrors.push("Ticket Subject is required.");
      newFieldErrors.subject = "Please enter a ticket subject.";
    } else if (subject.length < 5) {
      newErrors.push("Ticket Subject must be at least 5 characters.");
      newFieldErrors.subject = "Subject is too short (minimum 5 characters).";
    }

    if (!message) {
      newErrors.push("Message Body is required.");
      newFieldErrors.message = "Please enter a detailed description of the issue.";
    } else if (message.length < 10) {
      newErrors.push("Message Body must be at least 10 characters.");
      newFieldErrors.message = "Message description is too brief (minimum 10 characters).";
    }

    if (newErrors.length > 0) {
      e.preventDefault();
      setErrors(newErrors);
      setFieldErrors(newFieldErrors);
      setTimeout(() => {
        summaryRef.current?.focus();
        summaryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } else {
      setErrors([]);
      setFieldErrors({});
    }
  };

  return (
    <div className="max-w-xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-sans">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
        <Link href="/" className="hover:text-slate-900 transition-colors focus:ring-1 focus:ring-blue-500 px-1 rounded">
          Home
        </Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-900 font-medium">Support Desk</span>
      </nav>

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Registry Support Desk
        </h1>
        <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
          Need assistance with coordinate discrepancies, record lookups, or system errors? Open a support ticket below. Available Monday to Friday, 8:00 AM - 5:00 PM (GMT+8).
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        {/* Header decoration */}
        <div className="bg-slate-900 text-white p-6 sm:p-8">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[9px] font-semibold tracking-wider uppercase text-slate-300 mb-3">
            Support Desk
          </div>
          <h2 className="text-lg font-bold tracking-tight">
            Create Support Ticket
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Add a clear subject, category, and reference number so the demo request is easy to track.
          </p>
        </div>

        {/* Accessibility Guidelines Message */}
        <div className="p-6 sm:px-8 pb-0">
          <p className="text-[11px] text-gray-500 leading-relaxed bg-slate-50 p-3 rounded-lg border border-gray-100">
            A red asterisk (<span className="text-red-600 font-bold" aria-hidden="true">*</span>) indicates a required field.
          </p>
        </div>

        {/* Error Summary Panel */}
        {errors.length > 0 && (
          <div className="p-6 sm:px-8 pb-0">
            <div
              ref={summaryRef}
              tabIndex={-1}
              className="p-4 bg-red-50 border border-red-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
              aria-labelledby="errors-summary-title"
            >
              <div className="flex gap-2.5 items-start">
                <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
                <div>
                  <h3 id="errors-summary-title" className="text-xs font-bold text-red-950 uppercase tracking-wider">
                    Please check the required fields below before submitting
                  </h3>
                  <ul className="list-disc pl-4 mt-2 space-y-1 text-xs text-red-800">
                    {errors.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Support Ticket Submission Form */}
        <form
          id="system-support-form"
          action="/support/submit"
          method="post"
          onSubmit={handleSubmit}
          className="p-6 sm:p-8 space-y-5"
          noValidate
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="support-input-email" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                Your Email <span className="text-red-600 font-bold" aria-hidden="true">*</span>
              </label>
              <input
                id="support-input-email"
                type="email"
                name="email"
                placeholder="e.g., citizen@example.com"
                required
                aria-required="true"
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? "support-input-email-error" : "support-input-email-help"}
                className={`w-full bg-white border ${
                  fieldErrors.email ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
                } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 min-h-11`}
              />
              <p className="text-[10px] text-gray-400 mt-1" id="support-input-email-help">
                We will list the dispatch details to this email address.
              </p>
              {fieldErrors.email && (
                <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="support-input-email-error">
                  <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="support-input-category" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                Inquiry Category <span className="text-red-600 font-bold" aria-hidden="true">*</span>
              </label>
              <select
                id="support-input-category"
                name="category"
                required
                aria-required="true"
                aria-invalid={!!fieldErrors.category}
                aria-describedby={fieldErrors.category ? "support-input-category-error" : undefined}
                className={`w-full bg-white border ${
                  fieldErrors.category ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
                } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 text-slate-800 min-h-11`}
              >
                <option value="">-- Select Category --</option>
                <option value="Cadastral Index Mapping">Cadastral Index Mapping</option>
                <option value="Ownership Discrepancy">Ownership Discrepancy</option>
                <option value="Regional Classification Review">Regional Classification Review</option>
                <option value="System Technical Error">System Technical Error</option>
              </select>
              {fieldErrors.category && (
                <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="support-input-category-error">
                  <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.category}
                </p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="support-input-subject" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Ticket Subject <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <input
              id="support-input-subject"
              type="text"
              name="subject"
              placeholder="e.g., Coordinates overlap in boundary maps"
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.subject}
              aria-describedby={fieldErrors.subject ? "support-input-subject-error" : "support-input-subject-help"}
              className={`w-full bg-white border ${
                fieldErrors.subject ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 min-h-11`}
            />
            <p className="text-[10px] text-gray-400 mt-1" id="support-input-subject-help">
              A short description of your question or request.
            </p>
            {fieldErrors.subject && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="support-input-subject-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.subject}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="support-input-referenceNo" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Associated Record / Reference No. <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <input
              id="support-input-referenceNo"
              type="text"
              name="referenceNo"
              placeholder="e.g., LND-2026-0001"
              className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 placeholder-gray-400 font-mono min-h-11"
            />
            <p className="text-[10px] text-gray-400 mt-1">
              Provide an existing record number if the issue relates to a specific deed document.
            </p>
          </div>

          <div>
            <label htmlFor="support-input-message" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Message Body / Description <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <textarea
              id="support-input-message"
              name="message"
              rows={4}
              placeholder="e.g., Describe the issues regarding system alignment, boundary lines, or record indexing..."
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.message}
              aria-describedby={fieldErrors.message ? "support-input-message-error" : undefined}
              className={`w-full bg-white border ${
                fieldErrors.message ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400`}
            ></textarea>
            {fieldErrors.message && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="support-input-message-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.message}
              </p>
            )}
          </div>

          {/* Demo notice */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-2.5 items-start">
            <AlertCircle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-[10px] text-amber-800 leading-relaxed font-sans">
              <span className="font-bold text-amber-900 block" id="simulation-notice-title">Demo Notice</span>
              This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.
            </div>
          </div>

          <div className="pt-4 border-t border-gray-100 flex justify-end items-center">
            <button
               id="submit-support-ticket-btn"
               type="submit"
               className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm px-6 py-2.5 rounded-lg shadow-sm transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 min-h-[44px] flex items-center justify-center"
            >
              Submit support ticket
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
