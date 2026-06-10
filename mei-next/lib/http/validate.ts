import { z, ZodError } from "zod";
import { HttpError } from "./errors";

/**
 * Zod validation with Pydantic-shaped 422 errors so clients reading the
 * `errors` array keep working (see ../nextjs-migration/schema.md §2).
 */

export function zodToPydanticErrors(err: ZodError, root = "body") {
  return err.issues.map((issue) => ({
    type: issue.code === "invalid_type" && issue.message.includes("received undefined") ? "missing" : issue.code,
    loc: [root, ...issue.path],
    msg: issue.message,
    input: null as unknown,
  }));
}

export async function parseBody<S extends z.ZodTypeAny>(req: Request, schema: S): Promise<z.infer<S>> {
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    throw new HttpError(422, "Validation failed", [
      { type: "json_invalid", loc: ["body"], msg: "Invalid JSON body", input: null },
    ]);
  }
  const result = schema.safeParse(raw);
  if (!result.success) {
    throw new HttpError(422, "Validation failed", zodToPydanticErrors(result.error));
  }
  return result.data;
}

/** Legacy 24-char ObjectId-shaped id check → 400 (matches FastAPI routes). */
export function require24(value: string, name: string): void {
  if (typeof value !== "string" || value.length !== 24) {
    throw new HttpError(400, `${name} must be exactly 24 characters long`);
  }
}
