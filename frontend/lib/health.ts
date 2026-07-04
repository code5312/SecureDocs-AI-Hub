import { z } from "zod";

const serviceStateSchema = z.enum(["up", "down"]);
const healthSchema = z.object({
  status: z.enum(["healthy", "unhealthy"]),
  services: z.object({
    database: serviceStateSchema,
    redis: serviceStateSchema,
    object_storage: serviceStateSchema,
  }),
});

export type HealthStatus = z.infer<typeof healthSchema>;

export function fallbackHealthStatus(): HealthStatus {
  return {
    status: "unhealthy",
    services: { database: "down", redis: "down", object_storage: "down" },
  };
}

export async function getHealthStatus(): Promise<HealthStatus> {
  const baseUrl = process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost/api/v1";
  const response = await fetch(`${baseUrl}/health`, { cache: "no-store" });
  const payload: unknown = await response.json();
  return healthSchema.parse(payload);
}
