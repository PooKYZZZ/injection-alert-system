"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { CalendarDays, AlertCircle, CheckCircle2 } from "lucide-react";

export default function AppointmentsPage() {
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const summaryRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    const form = e.currentTarget;
    const formData = new FormData(form);
    
    const fullName = (formData.get("fullName") as string || "").trim();
    const email = (formData.get("email") as string || "").trim();
    const branch = formData.get("branch") as string || "";
    const serviceType = formData.get("serviceType") as string || "";
    const preferredDate = formData.get("preferredDate") as string || "";

    const newErrors: string[] = [];
    const newFieldErrors: Record<string, string> = {};

    if (!fullName) {
      newErrors.push("Full Name is required.");
      newFieldErrors.fullName = "Please enter your full legal name.";
    } else if (fullName.length < 2) {
      newErrors.push("Full Name must be at least 2 characters.");
      newFieldErrors.fullName = "Legal name is too short (minimum 2 characters).";
    }

    if (!email) {
      newErrors.push("Email Address is required.");
      newFieldErrors.email = "Please enter your email address.";
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        newErrors.push("Please enter a valid email address.");
        newFieldErrors.email = "The email address format is invalid (e.g., citizen@example.gov).";
      }
    }

    if (!branch) {
      newErrors.push("Regional Registry Branch selection is required.");
      newFieldErrors.branch = "Please select a branch office for your consultation.";
    }

    if (!serviceType) {
      newErrors.push("Service Consultation Type selection is required.");
      newFieldErrors.serviceType = "Please select the type of registry service needed.";
    }

    if (!preferredDate) {
      newErrors.push("Preferred Consultation Date is required.");
      newFieldErrors.preferredDate = "Please select a preferred date.";
    } else {
      const selected = new Date(preferredDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (selected < today) {
        newErrors.push("Preferred Consultation Date cannot be in the past.");
        newFieldErrors.preferredDate = "The selected date is in the past. Please schedule a future date.";
      }
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
        <span className="text-slate-900 font-medium">Book Appointment</span>
      </nav>

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Book Registrar Appointment
        </h1>
        <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
          Schedule an in-person consultation with local land surveyors or registrars. Administrative hours are Monday to Friday, 8:00 AM - 5:00 PM (GMT+8).
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        {/* Banner */}
        <div className="bg-slate-900 text-white p-6 sm:p-8">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[9px] font-semibold tracking-wider uppercase text-slate-300 mb-3">
            In-Office Bookings & Surveys
          </div>
          <h2 className="text-lg font-bold tracking-tight">
            Consultations & Survey Booking
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Fill out the details below to secure a consultation slot in your preferred regional office branch.
          </p>
        </div>

        {/* Accessibility Guidelines Message */}
        <div className="p-6 sm:px-8 pb-0">
          <p className="text-[11px] text-gray-500 leading-relaxed bg-slate-50 p-3 rounded-lg border border-gray-100">
            A red asterisk (<span className="text-red-600 font-bold" aria-hidden="true">*</span>) indicates a required field. Pre-validation checks prevent administrative entry errors.
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

        {/* Form representation */}
        <form
          id="registrar-appointment-form"
          action="/appointments/submit"
          method="post"
          onSubmit={handleSubmit}
          className="p-6 sm:p-8 space-y-5"
          noValidate
        >
          <div>
            <label htmlFor="appointment-input-fullName" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Full Name <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <input
              id="appointment-input-fullName"
              type="text"
              name="fullName"
              placeholder="e.g., Maria Santos"
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.fullName}
              aria-describedby={fieldErrors.fullName ? "appointment-input-fullName-error" : "appointment-input-fullName-help"}
              className={`w-full bg-white border ${
                fieldErrors.fullName ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 transition-colors min-h-11`}
            />
            <p className="text-[10px] text-gray-400 mt-1" id="appointment-input-fullName-help">
              Enter your full legal name as it appears on your title deeds or government IDs.
            </p>
            {fieldErrors.fullName && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="appointment-input-fullName-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.fullName}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="appointment-input-email" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Email Address <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <input
              id="appointment-input-email"
              type="email"
              name="email"
              placeholder="e.g., citizen@example.com"
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.email}
              aria-describedby={fieldErrors.email ? "appointment-input-email-error" : "appointment-input-email-help"}
              className={`w-full bg-white border ${
                fieldErrors.email ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 placeholder-gray-400 transition-colors min-h-11`}
            />
            <p className="text-[10px] text-gray-400 mt-1" id="appointment-input-email-help">
              The appointment confirmation and reservation token will be sent to this email.
            </p>
            {fieldErrors.email && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="appointment-input-email-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.email}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="appointment-input-branch" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                Regional Registry Branch <span className="text-red-600 font-bold" aria-hidden="true">*</span>
              </label>
              <select
                id="appointment-input-branch"
                name="branch"
                required
                aria-required="true"
                aria-invalid={!!fieldErrors.branch}
                aria-describedby={fieldErrors.branch ? "appointment-input-branch-error" : undefined}
                className={`w-full bg-white border ${
                  fieldErrors.branch ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
                } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 text-slate-800 min-h-11`}
              >
                <option value="">-- Select Branch --</option>
                <option value="Pasig Branch Office">Pasig Branch Office</option>
                <option value="Cainta Satellite Office">Cainta Satellite Office</option>
                <option value="Marikina Extension Desk">Marikina Extension Desk</option>
                <option value="Quezon City Registrar Headquarters">Quezon City Registrar Headquarters</option>
              </select>
              {fieldErrors.branch && (
                <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="appointment-input-branch-error">
                  <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.branch}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="appointment-input-serviceType" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                Service Consultation Type <span className="text-red-600 font-bold" aria-hidden="true">*</span>
              </label>
              <select
                id="appointment-input-serviceType"
                name="serviceType"
                required
                aria-required="true"
                aria-invalid={!!fieldErrors.serviceType}
                aria-describedby={fieldErrors.serviceType ? "appointment-input-serviceType-error" : undefined}
                className={`w-full bg-white border ${
                  fieldErrors.serviceType ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
                } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 text-slate-800 min-h-11`}
              >
                <option value="">-- Select Service --</option>
                <option value="Boundary Dispute Arbitration">Boundary Dispute Arbitration</option>
                <option value="Title Deed Transfer Processing">Title Deed Transfer Processing</option>
                <option value="Property Partitioning Consultation">Property Partitioning Consultation</option>
                <option value="Cadastral Map Blueprint Request">Cadastral Map Blueprint Request</option>
              </select>
              {fieldErrors.serviceType && (
                <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="appointment-input-serviceType-error">
                  <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.serviceType}
                </p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="appointment-input-preferredDate" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Preferred Consultation Date <span className="text-red-600 font-bold" aria-hidden="true">*</span>
            </label>
            <input
              id="appointment-input-preferredDate"
              type="date"
              name="preferredDate"
              required
              aria-required="true"
              aria-invalid={!!fieldErrors.preferredDate}
              aria-describedby={fieldErrors.preferredDate ? "appointment-input-preferredDate-error" : "appointment-input-preferredDate-help"}
              className={`w-full bg-white border ${
                fieldErrors.preferredDate ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-blue-600"
              } rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-offset-1 text-slate-800 min-h-11`}
            />
            <p className="text-[10px] text-gray-400 mt-1" id="appointment-input-preferredDate-help">
              Appointments are subject to registrar availability during normal working hours.
            </p>
            {fieldErrors.preferredDate && (
              <p className="text-[11px] text-red-600 font-medium mt-1.5 flex items-center gap-1" id="appointment-input-preferredDate-error">
                <AlertCircle className="h-3 w-3" aria-hidden="true" /> {fieldErrors.preferredDate}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="appointment-input-notes" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
              Supplementary Discussion Notes
            </label>
            <textarea
              id="appointment-input-notes"
              name="notes"
              rows={3}
              placeholder="e.g., Provide reference coordinates or plot information to help our surveyors prepare..."
              className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 placeholder-gray-400"
            ></textarea>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-2.5 items-start">
            <CalendarDays className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-[10px] text-amber-800 leading-relaxed font-sans">
              <span className="font-bold text-amber-900 block" id="simulation-notice-title">Demo Notice</span>
              This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.
            </div>
          </div>

          <div className="pt-4 border-t border-gray-100 flex justify-end items-center">
            <button
              id="submit-appointment-btn"
              type="submit"
              className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm px-6 py-2.5 rounded-lg shadow-sm transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 min-h-[44px] flex items-center justify-center"
            >
              Request appointment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
