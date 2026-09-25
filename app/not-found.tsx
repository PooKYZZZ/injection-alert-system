import { HttpErrorPage } from "../components/HttpErrorPage";

export default function NotFound() {
  return <HttpErrorPage status={404} />;
}
