import {
  httpErrorPageMarkup,
  type HttpErrorStatus,
} from "../lib/http-error-page";

export function HttpErrorPage({
  status,
  retryAfterSeconds,
}: {
  status: HttpErrorStatus;
  retryAfterSeconds?: number;
}) {
  return (
    <div
      dangerouslySetInnerHTML={{
        __html: httpErrorPageMarkup(status, retryAfterSeconds),
      }}
    />
  );
}
