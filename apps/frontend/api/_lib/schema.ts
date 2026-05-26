import { z } from "zod";

export const ArticleFilingSchema = z.object({
  article: z.string().min(1),
});

export const LeadFilingSchema = z.object({
  lead_headline: z.string().max(160),
  lead_body: z.string().max(600),
  active_count: z.coerce.number().int().min(0),
  project_lines: z.array(
    z.object({
      slug: z.string(),
      name: z.string(),
      status: z.string(),
      stat: z.string(),
      bullet: z.enum(["red", "amber", "sand"]),
    })
  ),
});

export const AddendumFilingSchema = z.object({
  label: z.string(),
  body: z.string().max(200),
});
