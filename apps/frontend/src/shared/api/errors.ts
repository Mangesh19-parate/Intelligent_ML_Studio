export class ApiError extends Error {
  public status: number;
  public data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export const normalizeApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) {
    return error;
  }
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const axiosError = error as { response?: { status?: number; data?: { detail?: string; message?: string } } };
    const status = axiosError.response?.status ?? 500;
    const detail = axiosError.response?.data?.detail || axiosError.response?.data?.message || 'An unexpected API error occurred';
    return new ApiError(detail, status, axiosError.response?.data);
  }
  if (error instanceof Error) {
    return new ApiError(error.message, 500);
  }
  return new ApiError('Unknown error occurred', 500);
};
