export interface LandRecord {
  recordNo: string;
  owner: string;
  location: string;
  type: string;
  size: string;
  status: string;
  classification: string;
  surveyDate: string;
}

export const MOCK_RECORDS: LandRecord[] = [
  {
    recordNo: "LND-2026-0001",
    owner: "Maria Santos",
    location: "Sect 9, North District Registry Sector",
    type: "Cultivation Yard",
    size: "450 sqm",
    status: "Active / Registered",
    classification: "Residential",
    surveyDate: "2026-01-14",
  },
  {
    recordNo: "LND-2026-0002",
    owner: "Daniel Reyes",
    location: "742 Evergreen Terrace, North Branch",
    type: "Residential",
    size: "1.2 hectares",
    status: "Collateralized",
    classification: "Commercial",
    surveyDate: "2019-11-22",
  },
  {
    recordNo: "LND-2026-0003",
    owner: "Elena Cruz",
    location: "1007 Mountain Drive, Crest Branch Municipal",
    type: "Commercial",
    size: "5.4 hectares",
    status: "Historical Preserve",
    classification: "Mixed Use",
    surveyDate: "2015-05-09",
  },
  {
    recordNo: "LND-2026-0004",
    owner: "Ramon Garcia",
    location: "10880 Malibu Point, South Branch Cliffside",
    type: "Agricultural",
    size: "2.1 hectares",
    status: "Active / Highly Monitored",
    classification: "Mixed Use",
    surveyDate: "2021-08-11",
  },
];
