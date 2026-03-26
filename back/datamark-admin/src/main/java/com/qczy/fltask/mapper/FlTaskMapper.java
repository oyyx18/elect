package com.qczy.fltask.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.qczy.fltask.model.entity.FlTaskEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface FlTaskMapper extends BaseMapper<FlTaskEntity> {
}
