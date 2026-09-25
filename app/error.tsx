"use client";

import { HttpErrorPage } from "../components/HttpErrorPage";

export default function ErrorPage() {
  return <HttpErrorPage status={500} />;
}
