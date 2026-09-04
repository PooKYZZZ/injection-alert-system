import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const args = process.argv.slice(2);

function argument(name, fallback) {
  const index = args.indexOf(name);
  return index === -1 ? fallback : args[index + 1];
}

function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function safeSheetName(fileName, usedNames) {
  const base = fileName
    .replace(/\.csv$/i, "")
    .replace(/[:\\/?*\[\]]/g, "-")
    .slice(0, 31) || "CSV";
  let name = base;
  let suffix = 1;
  while (usedNames.has(name)) {
    const suffixText = `-${suffix}`;
    name = `${base.slice(0, 31 - suffixText.length)}${suffixText}`;
    suffix += 1;
  }
  usedNames.add(name);
  return name;
}

const SOURCE_SHEET_CONFIG = {
  "panel-results-final.csv": { sheetName: "Panel Final - Mixed Cases", tableName: "tblPanelFinalMixedCases" },
  "panel-results.csv": { sheetName: "Panel Results - Mixed Cases", tableName: "tblPanelResultsMixedCases" },
  "search-records-code-expansion-20260903.csv": {
    sheetName: "Code Expansion - Code Injection",
    tableName: "tblCodeExpansionCodeInjection",
  },
  "search-records-full-before-code-expansion-20260903.csv": {
    sheetName: "Full Baseline - All Attacks",
    tableName: "tblFullBaselineAllAttacks",
  },
  "search-records-full.csv": { sheetName: "Full Results - All Attacks", tableName: "tblFullResultsAllAttacks" },
  "search-records-normal-baseline-20260903.csv": {
    sheetName: "Normal Baseline - Benign",
    tableName: "tblNormalBaselineBenign",
  },
  "search-records-seeds-before-code-expansion-20260903.csv": {
    sheetName: "Seeds Baseline - All Attacks",
    tableName: "tblSeedsBaselineAllAttacks",
  },
  "search-records-seeds-r2.csv": { sheetName: "Seeds R2 - All Attacks", tableName: "tblSeedsR2AllAttacks" },
  "search-records-seeds.csv": { sheetName: "Seeds - SQL Injection", tableName: "tblSeedsSqlInjection" },
};

function sourceSheetConfig(fileName, usedNames) {
  const configured = SOURCE_SHEET_CONFIG[fileName];
  if (configured && !usedNames.has(configured.sheetName)) {
    usedNames.add(configured.sheetName);
    return configured;
  }
  return {
    sheetName: safeSheetName(fileName, usedNames),
    tableName: `tbl${fileName.replace(/[^A-Za-z0-9]/g, "")}`.slice(0, 240),
  };
}

function widthForHeader(header, values, { focused = false } = {}) {
  const normalized = header.toLowerCase();
  const longText = [
    "payload",
    "wire_query",
    "description",
    "source_seed_payload",
    "selection_tags",
    "error",
  ].some((term) => normalized.includes(term));
  const maxValueLength = values.reduce((max, value) => {
    const length = String(value ?? "").length;
    return Math.max(max, length);
  }, header.length);
  const cap = longText ? (focused ? 90 : 48) : 30;
  const scaled = Math.ceil(Math.min(maxValueLength, cap) * 1.05) + 2;
  return Math.max(10, Math.min(cap, scaled));
}

function styleSheet(sheet, values, { focused = false } = {}) {
  const rowCount = values.length;
  const columnCount = values[0]?.length ?? 0;
  if (rowCount === 0 || columnCount === 0) return;

  const lastColumn = columnName(columnCount - 1);
  const usedRange = sheet.getRange(`A1:${lastColumn}${rowCount}`);
  const headerRange = sheet.getRange(`A1:${lastColumn}1`);

  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  headerRange.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#B4C7E7" },
  };
  headerRange.format.rowHeight = 34;
  usedRange.format.font = { name: "Aptos", size: 10 };

  const headers = values[0].map((value) => String(value ?? ""));
  headers.forEach((header, index) => {
    const column = columnName(index);
    const columnValues = values.slice(1).map((row) => row[index]);
    const columnRange = sheet.getRange(`${column}1:${column}${rowCount}`);
    columnRange.format.columnWidth = widthForHeader(header, [header, ...columnValues], { focused });
    if (
      ["payload", "wire_query", "description", "source_seed_payload", "selection_tags", "error"].some(
        (term) => header.toLowerCase().includes(term),
      )
    ) {
      sheet.getRange(`${column}2:${column}${rowCount}`).format.wrapText = true;
    }
  });

  const bodyRange = rowCount > 1 ? sheet.getRange(`A2:${lastColumn}${rowCount}`) : null;
  if (bodyRange) {
    bodyRange.format.borders = {
      insideHorizontal: { style: "thin", color: "#E6EAF0" },
      bottom: { style: "thin", color: "#D9E2F3" },
    };
    if (focused) bodyRange.format.autofitRows();
  }
}

function addExcelTable(sheet, values, tableName) {
  const rowCount = values.length;
  const columnCount = values[0]?.length ?? 0;
  if (rowCount === 0 || columnCount === 0) return null;
  const lastColumn = columnName(columnCount - 1);
  return sheet.tables.add(`A1:${lastColumn}${rowCount}`, true, tableName);
}

function rowObjects(values) {
  const headers = values[0].map((value) => String(value ?? ""));
  return values.slice(1).map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])),
  );
}

function valueOf(row, key) {
  return row[key] ?? "";
}

const PAYLOAD_HEADERS = [
  "case_id",
  "group",
  "payload",
  "wire_query",
  "source_seed_payload",
  "expected_label",
  "predicted_label",
  "classification_correct",
  "confidence",
  "confidence_level",
  "mutation",
  "seed_id",
  "source_file",
];

function payloadRow(sourceFile, group, row) {
  return PAYLOAD_HEADERS.map((header) => {
    if (header === "source_file") return sourceFile;
    if (header === "group") return group;
    return valueOf(row, header);
  });
}

function addPayloadSheet(workbook, { sheetName, tableName, rows }) {
  const sheet = workbook.worksheets.add(sheetName);
  const values = [PAYLOAD_HEADERS, ...rows];
  const lastColumn = columnName(PAYLOAD_HEADERS.length - 1);
  sheet.getRange(`A1:${lastColumn}${values.length}`).values = values;
  styleSheet(sheet, values, { focused: true });
  const table = addExcelTable(sheet, values, tableName);
  return { sheet, values, table, rows: rows.length, columns: PAYLOAD_HEADERS.length, tableName, sheetName };
}

async function addReadme(workbook, sourceMetadata, payloadSummaries) {
  const sheet = workbook.worksheets.add("README");
  sheet.showGridLines = false;
  const rawDescription = sourceMetadata
    .map((summary) => `${summary.sheetName} [${summary.tableName}]`)
    .join("; ");
  const payloadDescription = payloadSummaries
    .map((summary) => `${summary.sheetName} [${summary.tableName}]: ${summary.rows} cases`)
    .join("; ");
  sheet.getRange("A1:B9").values = [
    ["Readable attack-test CSV workbook", ""],
    ["Purpose", "Human-readable view of every CSV currently under output/attack-tests."],
    ["Important", "The original CSV files were not padded or rewritten; exact payloads and machine-readable values remain unchanged."],
    ["Why", "CSV has no visual column-width metadata. This workbook supplies widths, wrapped long fields, a frozen header row, and clear boundaries."],
    ["Payload tabs", payloadDescription],
    ["Raw result tabs", rawDescription],
    ["Source directory", "output/attack-tests"],
    ["Exact payload fields", "Each Payload tab includes the complete payload in the payload column and the complete encoded request in the wire_query column."],
    ["How to use", "Use the four Payload tabs for the complete payload and encoded wire query. Use the named raw tabs for the full evidence columns."],
  ];
  sheet.mergeCells("A1:B1");
  sheet.getRange("A1:B1").format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF", size: 14 },
  };
  sheet.getRange("A2:A9").format = {
    fill: "#D9EAF7",
    font: { bold: true, color: "#1F1F1F" },
  };
  sheet.getRange("A1:B9").format.borders = {
    preset: "all",
    style: "thin",
    color: "#B4C7E7",
  };
  sheet.getRange("A1:B9").format.wrapText = true;
  sheet.getRange("A1:B1").format.rowHeight = 28;
  sheet.getRange("A1:A9").format.columnWidth = 18;
  sheet.getRange("B1:B9").format.columnWidth = 72;
}

async function main() {
  const inputDir = path.resolve(argument("--input-dir", "output/attack-tests"));
  const outputPath = path.resolve(
    argument("--output", path.join(inputDir, "search-records-attack-outputs-readable.xlsx")),
  );
  const previewDir = path.resolve(argument("--preview-dir", path.join(inputDir, ".readable-previews")));

  const entries = await fs.readdir(inputDir, { withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".csv"))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right));
  if (files.length === 0) throw new Error(`No CSV files found in ${inputDir}`);

  const usedSheetNames = new Set(["README"]);
  const sourceData = new Map();

  for (const fileName of files) {
    const text = await fs.readFile(path.join(inputDir, fileName), "utf8");
    const config = sourceSheetConfig(fileName, usedSheetNames);
    const importedWorkbook = await Workbook.fromCSV(text, { sheetName: config.sheetName });
    const importedSheet = importedWorkbook.worksheets.getItem(config.sheetName);
    const values = importedSheet.getUsedRange(true).values;
    sourceData.set(fileName, { config, values, rows: rowObjects(values) });
  }

  const fullResults = sourceData.get("search-records-full.csv")?.rows ?? [];
  const codeExpansion = sourceData.get("search-records-code-expansion-20260903.csv")?.rows ?? [];
  const normalBaseline = sourceData.get("search-records-normal-baseline-20260903.csv")?.rows ?? [];
  const payloadPlans = [
    {
      sheetName: "Payloads - SQL Injection",
      tableName: "tblPayloadsSqlInjection",
      rows: fullResults
        .filter((row) => valueOf(row, "family") === "sql_injection")
        .map((row) => payloadRow("search-records-full.csv", "SQL Injection baseline", row)),
    },
    {
      sheetName: "Payloads - Code Injection",
      tableName: "tblPayloadsCodeInjection",
      rows: [
        ...fullResults
          .filter((row) => valueOf(row, "family") === "code_injection")
          .map((row) => payloadRow("search-records-full.csv", "Original Code Injection baseline", row)),
        ...codeExpansion.map((row) =>
          payloadRow("search-records-code-expansion-20260903.csv", "Expanded Code Injection variations", row),
        ),
      ],
    },
    {
      sheetName: "Payloads - General Attacks",
      tableName: "tblPayloadsGeneralAttacks",
      rows: fullResults
        .filter((row) => valueOf(row, "family") === "general_attack")
        .map((row) => payloadRow("search-records-full.csv", "General attack baseline", row)),
    },
    {
      sheetName: "Payloads - Normal Traffic",
      tableName: "tblPayloadsNormalTraffic",
      rows: normalBaseline
        .filter((row) => valueOf(row, "family") === "normal_traffic")
        .map((row) => payloadRow("search-records-normal-baseline-20260903.csv", "Normal / benign baseline", row)),
    },
  ];

  const workbook = Workbook.create();
  const payloadMetadata = payloadPlans.map((plan) => ({
    sheetName: plan.sheetName,
    tableName: plan.tableName,
    rows: plan.rows.length,
  }));
  const sourceMetadata = files.map((fileName) => {
    const { config } = sourceData.get(fileName);
    return { fileName, sheetName: config.sheetName, tableName: config.tableName };
  });
  await addReadme(workbook, sourceMetadata, payloadMetadata);
  const summaries = [];
  for (const fileName of files) {
    const { config, values } = sourceData.get(fileName);
    const sheet = workbook.worksheets.add(config.sheetName);
    const lastColumn = columnName((values[0]?.length ?? 1) - 1);
    const lastRow = Math.max(1, values.length);
    sheet.getRange(`A1:${lastColumn}${lastRow}`).values = values;
    styleSheet(sheet, values);
    addExcelTable(sheet, values, config.tableName);
    summaries.push({
      fileName,
      sheetName: config.sheetName,
      tableName: config.tableName,
      rows: Math.max(0, values.length - 1),
      columns: values[0]?.length ?? 0,
    });
  }

  const payloadSummaries = payloadPlans.map((plan) => addPayloadSheet(workbook, plan));

  await fs.mkdir(previewDir, { recursive: true });
  const previewSummaries = [
    { fileName: "README", sheetName: "README", rows: 9, columns: 2 },
    ...summaries,
    ...payloadSummaries.map((summary) => ({
      fileName: summary.sheetName,
      sheetName: summary.sheetName,
      tableName: summary.tableName,
      rows: summary.rows,
      columns: summary.columns,
    })),
  ];
  for (const summary of previewSummaries) {
    const sheet = workbook.worksheets.getItem(summary.sheetName);
    const previewLastRow = summary.sheetName === "README" ? 9 : Math.min(summary.rows + 1, 8);
    const previewLastColumn = columnName(Math.max(0, summary.columns - 1));
    const preview = await workbook.render({
      sheetName: summary.sheetName,
      range: `A1:${previewLastColumn}${previewLastRow}`,
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      path.join(previewDir, `${summary.sheetName.replace(/[^A-Za-z0-9_-]/g, "_")}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);

  const roundTrip = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
  const roundTripSheets = previewSummaries.map((summary) => {
    const values = roundTrip.worksheets.getItem(summary.sheetName).getUsedRange(true).values;
    const tableNames = roundTrip.worksheets
      .getItem(summary.sheetName)
      .tables.items.map((table) => table.name);
    return {
      sheetName: summary.sheetName,
      rows: summary.sheetName === "README" ? values.length : Math.max(0, values.length - 1),
      columns: values[0]?.length ?? 0,
      tableName: summary.tableName ?? null,
      tableNameFound: summary.tableName ? tableNames.includes(summary.tableName) : true,
    };
  });
  const payloadRoundTrip = payloadSummaries.map((summary) => {
    const actualValues = roundTrip.worksheets.getItem(summary.sheetName).getUsedRange(true).values;
    const payloadAndWireMatch =
      actualValues.length === summary.values.length &&
      summary.values.slice(1).every((row, index) => {
        const actual = actualValues[index + 1] ?? [];
        return String(row[2] ?? "") === String(actual[2] ?? "") && String(row[3] ?? "") === String(actual[3] ?? "");
      });
    return { sheetName: summary.sheetName, rows: summary.rows, payloadAndWireMatch };
  });
  const roundTripMatches = roundTripSheets.every((sheet, index) => {
    const expected = previewSummaries[index];
    return (
      sheet.rows === expected.rows &&
      sheet.columns === expected.columns &&
      sheet.tableNameFound
    );
  }) && payloadRoundTrip.every((summary) => summary.payloadAndWireMatch);
  if (!roundTripMatches) {
    console.error(JSON.stringify({ expected: previewSummaries, actual: roundTripSheets }, null, 2));
    throw new Error("XLSX round-trip validation changed a sheet shape");
  }

  console.log(
    JSON.stringify(
      { outputPath, sourceCount: files.length, roundTripMatches, sheets: summaries, payloadSheets: payloadRoundTrip },
      null,
      2,
    ),
  );
}

await main();
