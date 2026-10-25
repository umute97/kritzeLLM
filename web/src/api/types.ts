import type { components } from './schema'

// Short names for the API's schemas. The schema itself is generated from api/openapi.json
// (`npm run api-types`), never edited by hand.
type Schemas = components['schemas']

export type Journal = Schemas['Journal']
export type JournalList = Schemas['JournalList']
export type Page = Schemas['Page']
export type PageDetail = Schemas['PageDetail']
export type PageList = Schemas['PageList']
export type PageStatus = Schemas['PageStatus']
export type Block = Schemas['Block']
export type Job = Schemas['Job']
export type UploadResult = Schemas['UploadResult']
export type Health = Schemas['Health']
export type Problem = Schemas['Problem']
