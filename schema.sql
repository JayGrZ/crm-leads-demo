-- Tabla de negocios (leads) para el CRM
-- Ejecutar en Supabase SQL Editor si necesitas recrear la tabla

CREATE TABLE IF NOT EXISTS public.negocios (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT,
    telefono TEXT,
    categoria TEXT,
    barrio TEXT,
    poblacion INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'Sin llamar',
    comentarios TEXT,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);

-- Índices útiles para filtros
CREATE INDEX IF NOT EXISTS idx_negocios_barrio ON public.negocios(barrio);
CREATE INDEX IF NOT EXISTS idx_negocios_categoria ON public.negocios(categoria);
CREATE INDEX IF NOT EXISTS idx_negocios_estado ON public.negocios(estado);
CREATE INDEX IF NOT EXISTS idx_negocios_telefono ON public.negocios(telefono);
