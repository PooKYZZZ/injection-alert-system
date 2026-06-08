// Centralized configuration and properties for the Land Records Demo Portal
// Used across client and server files to keep public demo copy consistent.

export const SITE_CONFIG = {
  name: "Land Records Demo Portal",
  acronym: "LRDP-PORTAL",
  officeHours: "Monday to Friday, 8:00 AM - 5:05 PM (GMT+8)",
  governingBody: "National Land Cadastre & Mapping Office",
  sandboxDisclaimer: "This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.",
};

export const BRANCHES = [
  { id: "pasig", name: "Pasig Branch Office", code: "PSG-01", address: "Meralco Avenue, Pasig City" },
  { id: "cainta", name: "Cainta Satellite Office", code: "CNT-02", address: "Ortigas Avenue Extension, Cainta" },
  { id: "marikina", name: "Marikina Extension Desk", code: "MRK-03", address: "Shoe Avenue, Marikina City" },
  { id: "quezon", name: "Quezon City Registrar Headquarters", code: "QCH-HQ", address: "East Avenue, Diliman, Quezon City" },
];

export const SERVICE_TYPES = [
  { id: "dispute", name: "Boundary Dispute Arbitration", duration: "Usually takes 45-60 mins" },
  { id: "deed_transfer", name: "Title Deed Transfer Processing", duration: "Requires reference number" },
  { id: "partition", name: "Property Partitioning Consultation", duration: "Takes 30 mins" },
  { id: "blueprint", name: "Cadastral Map Blueprint Request", duration: "Completed digitally" },
];

export const SUPPORT_CATEGORIES = [
  "Cadastral Index Mapping",
  "Ownership Discrepancy",
  "Regional Classification Review",
  "System Technical Error",
];

export const DELIVERY_OPTIONS = [
  { id: "digital", label: "Digital copy", description: "Demo copy summary" },
  { id: "physical", label: "Printed certified copy", description: "Demo print request" },
];
