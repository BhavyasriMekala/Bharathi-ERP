import api from "./axiosConfig";

export const getBharathiDashboard = () => api.get("/bharathi/dashboard");
export const listBharathiSupplierSummary = () => api.get("/bharathi/suppliers/summary");
export const getBharathiBill = (id) => api.get(`/bharathi/bills/${id}`);
export const listBharathiBills = (params) => api.get("/bharathi/bills", { params });
export const listBharathiBillsPaginated = (params) =>
  api.get("/bharathi/bills", { params: { ...params, paginate: true } });
export const createBharathiBill = (payload) => api.post("/bharathi/bills", payload);
export const submitBharathiBill = (id) => api.post(`/bharathi/bills/${id}/submit`);
export const verifyBharathiBill = (id, payload) => api.post(`/bharathi/bills/${id}/verify`, payload);
export const approveBharathiBill = (id, payload) => api.post(`/bharathi/bills/${id}/approve`, payload);
export const getBharathiBillAudit = (id) => api.get(`/bharathi/bills/${id}/audit`);
export const getCollectionsOutstanding = () => api.get("/bharathi/collections/outstanding");
export const runTallySync = (payload) => api.post("/bharathi/tally/sync", payload);
export const getTallyReadonlyPoc = () => api.get("/bharathi/tally/readonly-poc");