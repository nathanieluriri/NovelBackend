/**
 * HttpError mirrors FastAPI's HTTPException. Thrown anywhere in a handler and
 * converted to the v2 error envelope by withRoute() (see ./route.ts and
 * ../nextjs-migration/schema.md §2).
 */
export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly errors?: unknown,
  ) {
    super(message);
    this.name = "HttpError";
  }
}
