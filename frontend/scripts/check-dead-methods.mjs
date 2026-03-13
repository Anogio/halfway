#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import * as ts from "typescript";

const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SRC_DIR = path.join(ROOT_DIR, "src");
const ALLOWED_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
const NEXT_SPECIAL_EXPORTS = new Set([
  "generateMetadata",
  "generateStaticParams",
  "generateImageMetadata",
  "generateSitemaps",
  "GET",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "HEAD",
  "OPTIONS"
]);

function collectSourceFiles(dirPath) {
  const stack = [dirPath];
  const files = [];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const absolutePath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(absolutePath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      if (entry.name.endsWith(".d.ts")) {
        continue;
      }
      const extension = path.extname(entry.name);
      if (ALLOWED_EXTENSIONS.has(extension)) {
        files.push(absolutePath);
      }
    }
  }

  return files.sort();
}

function scriptKindForPath(filePath) {
  if (filePath.endsWith(".tsx")) {
    return ts.ScriptKind.TSX;
  }
  if (filePath.endsWith(".ts")) {
    return ts.ScriptKind.TS;
  }
  if (filePath.endsWith(".jsx")) {
    return ts.ScriptKind.JSX;
  }
  if (filePath.endsWith(".mjs")) {
    return ts.ScriptKind.JS;
  }
  return ts.ScriptKind.JS;
}

function hasModifier(node, modifierKind) {
  return (node.modifiers ?? []).some((modifier) => modifier.kind === modifierKind);
}

function isDefaultExport(node) {
  return hasModifier(node, ts.SyntaxKind.DefaultKeyword);
}

function isFunctionLikeInitializer(initializer) {
  return (
    ts.isArrowFunction(initializer) ||
    ts.isFunctionExpression(initializer)
  );
}

function isNextSpecialExport(filePath, exportName) {
  if (!filePath.includes(`${path.sep}src${path.sep}app${path.sep}`)) {
    return false;
  }
  return NEXT_SPECIAL_EXPORTS.has(exportName);
}

function countIdentifierOccurrences(text, identifier) {
  const escaped = identifier.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`\\b${escaped}\\b`, "g");
  const matches = text.match(regex);
  return matches ? matches.length : 0;
}

function toRelative(filePath) {
  return path.relative(ROOT_DIR, filePath).replaceAll(path.sep, "/");
}

function extractExportedMethods(filePath, sourceFile) {
  const exportedMethods = [];

  for (const statement of sourceFile.statements) {
    if (ts.isFunctionDeclaration(statement)) {
      if (
        !statement.name ||
        !hasModifier(statement, ts.SyntaxKind.ExportKeyword) ||
        isDefaultExport(statement)
      ) {
        continue;
      }
      exportedMethods.push({
        name: statement.name.text,
        line: sourceFile.getLineAndCharacterOfPosition(statement.getStart(sourceFile)).line + 1
      });
      continue;
    }

    if (!ts.isVariableStatement(statement) || !hasModifier(statement, ts.SyntaxKind.ExportKeyword)) {
      continue;
    }

    for (const declaration of statement.declarationList.declarations) {
      if (!ts.isIdentifier(declaration.name) || !declaration.initializer) {
        continue;
      }
      if (!isFunctionLikeInitializer(declaration.initializer)) {
        continue;
      }
      exportedMethods.push({
        name: declaration.name.text,
        line: sourceFile.getLineAndCharacterOfPosition(declaration.getStart(sourceFile)).line + 1
      });
    }
  }

  return exportedMethods;
}

const sourceFiles = collectSourceFiles(SRC_DIR);
const sourcesByPath = new Map();

for (const filePath of sourceFiles) {
  const content = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    content,
    ts.ScriptTarget.Latest,
    true,
    scriptKindForPath(filePath)
  );
  sourcesByPath.set(filePath, { content, sourceFile });
}

const findings = [];

for (const [filePath, { sourceFile }] of sourcesByPath) {
  const exportedMethods = extractExportedMethods(filePath, sourceFile);
  for (const method of exportedMethods) {
    if (isNextSpecialExport(filePath, method.name)) {
      continue;
    }

    let occurrences = 0;
    for (const { content } of sourcesByPath.values()) {
      occurrences += countIdentifierOccurrences(content, method.name);
      if (occurrences > 1) {
        break;
      }
    }

    if (occurrences <= 1) {
      findings.push({
        ...method,
        filePath
      });
    }
  }
}

if (findings.length === 0) {
  console.log("No dead exported methods found in src.");
  process.exit(0);
}

console.error("Dead exported methods (no in-src references):");
for (const finding of findings) {
  console.error(`- ${toRelative(finding.filePath)}:${finding.line} ${finding.name}`);
}
process.exit(1);
