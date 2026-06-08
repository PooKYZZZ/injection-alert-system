/**
 * Centralized, simple, type-safe validation helpers for forms.
 * Follows rigid guidelines - checks required fields, email formatting,
 * and maintains calm, helpful, non-technical error microcopy.
 */

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  fieldErrors: Record<string, string>;
}

/**
 * Validates a standard email string.
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validates Support Form payload
 */
export function validateSupportForm(data: {
  email?: string;
  category?: string;
  subject?: string;
  message?: string;
}): ValidationResult {
  const errors: string[] = [];
  const fieldErrors: Record<string, string> = {};

  const email = (data.email || "").trim();
  const category = (data.category || "").trim();
  const subject = (data.subject || "").trim();
  const message = (data.message || "").trim();

  if (!email) {
    errors.push("Your Email address is required.");
    fieldErrors.email = "Please enter your email address.";
  } else if (!isValidEmail(email)) {
    errors.push("Please enter a valid email address.");
    fieldErrors.email = "The email address format is invalid (e.g., citizen@example.com).";
  }

  if (!category) {
    errors.push("Inquiry Category selection is required.");
    fieldErrors.category = "Please select an inquiry category.";
  }

  if (!subject) {
    errors.push("Ticket Subject is required.");
    fieldErrors.subject = "Please enter a ticket subject.";
  } else if (subject.length < 5) {
    errors.push("Ticket Subject must be at least 5 characters.");
    fieldErrors.subject = "Subject description is too short (minimum 5 characters).";
  }

  if (!message) {
    errors.push("Message Body is required.");
    fieldErrors.message = "Please enter a detailed description of the issue.";
  } else if (message.length < 10) {
    errors.push("Message Body must be at least 10 characters.");
    fieldErrors.message = "Description needs more detail (minimum 10 characters).";
  }

  return {
    isValid: errors.length === 0,
    errors,
    fieldErrors,
  };
}

/**
 * Validates Appointment Booking payload
 */
export function validateAppointmentForm(data: {
  fullName?: string;
  email?: string;
  branch?: string;
  serviceType?: string;
  preferredDate?: string;
}): ValidationResult {
  const errors: string[] = [];
  const fieldErrors: Record<string, string> = {};

  const fullName = (data.fullName || "").trim();
  const email = (data.email || "").trim();
  const branch = (data.branch || "").trim();
  const serviceType = (data.serviceType || "").trim();
  const preferredDate = (data.preferredDate || "").trim();

  if (!fullName) {
    errors.push("Full Legal Name is required.");
    fieldErrors.fullName = "Please enter your full legal name.";
  } else if (fullName.length < 2) {
    errors.push("Legal name must be at least 2 characters.");
    fieldErrors.fullName = "Name is too short (minimum 2 characters).";
  }

  if (!email) {
    errors.push("Email Address is required.");
    fieldErrors.email = "Please enter your email address.";
  } else if (!isValidEmail(email)) {
    errors.push("Please enter a valid email address.");
    fieldErrors.email = "The email address format is invalid (e.g., citizen@example.com).";
  }

  if (!branch) {
    errors.push("Regional Registry Branch selection is required.");
    fieldErrors.branch = "Please select an office branch for your visit.";
  }

  if (!serviceType) {
    errors.push("Service Type selection is required.");
    fieldErrors.serviceType = "Please select the type of registry service needed.";
  }

  if (!preferredDate) {
    errors.push("Preferred Consultation Date is required.");
    fieldErrors.preferredDate = "Please choose a valid scheduling date.";
  } else {
    const selected = new Date(preferredDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (selected < today) {
      errors.push("Preferred Consultation Date cannot be in the past.");
      fieldErrors.preferredDate = "The selected date has already passed. Please select a future date.";
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    fieldErrors,
  };
}

/**
 * Validates Certified Copy Request payload
 */
export function validateCopyForm(data: {
  fullName?: string;
  email?: string;
  purpose?: string;
  deliveryOption?: string;
}): ValidationResult {
  const errors: string[] = [];
  const fieldErrors: Record<string, string> = {};

  const fullName = (data.fullName || "").trim();
  const email = (data.email || "").trim();
  const purpose = (data.purpose || "").trim();
  const deliveryOption = (data.deliveryOption || "").trim();

  if (!fullName) {
    errors.push("Full Legal Name is required.");
    fieldErrors.fullName = "Please enter your full legal name.";
  } else if (fullName.length < 2) {
    errors.push("Legal name must be at least 2 characters.");
    fieldErrors.fullName = "Name is too short.";
  }

  if (!email) {
    errors.push("Email Address is required.");
    fieldErrors.email = "Please enter your email address.";
  } else if (!isValidEmail(email)) {
    errors.push("Please enter a valid email address.");
    fieldErrors.email = "The email address format is invalid.";
  }

  if (!purpose) {
    errors.push("Purpose of Request selection is required.");
    fieldErrors.purpose = "Please select a request purpose option.";
  }

  if (!deliveryOption) {
    errors.push("Delivery Option selection is required.");
    fieldErrors.deliveryOption = "Please select a certified delivery option.";
  }

  return {
    isValid: errors.length === 0,
    errors,
    fieldErrors,
  };
}

/**
 * Validates Registrar demo-login payload (authentication disabled)
 */
export function validateLoginForm(data: {
  username?: string;
  password?: string;
}): ValidationResult {
  const errors: string[] = [];
  const fieldErrors: Record<string, string> = {};

  const username = (data.username || "").trim();
  const password = (data.password || "").trim();

  if (!username) {
    errors.push("Please enter your database username.");
    fieldErrors.username = "Username field cannot be empty.";
  }

  if (!password) {
    errors.push("Please enter your surveyor password.");
    fieldErrors.password = "Password field cannot be empty.";
  }

  return {
    isValid: errors.length === 0,
    errors,
    fieldErrors,
  };
}
